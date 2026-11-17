#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Read-only SCSI pass-through to a physical disk behind an MFI MegaRAID
controller (MFI_CMD_PD_SCSI_IO) through /dev/megaraid_sas_ioctl_node.

Works with the stock megaraid_sas driver: use it to check whether your
controller firmware accepts media READ commands sent straight to a physical
disk, before installing the patched driver.

usage: mfi_pt.py <host_no> <device_id> inquiry
       mfi_pt.py <host_no> <device_id> cap
       mfi_pt.py <host_no> <device_id> read <lba> [blocks] [output-file]

host_no   = SCSI host number of the controller (N in /sys/class/scsi_host/hostN
            whose proc_name is megaraid_sas)
device_id = "Device Id" from `storcli64 /c0/eall/sall show` (DID column)
            or `MegaCli64 -PDList -aALL`
Only commands that read are implemented. Blocks are assumed to be 512 bytes.
"""
import ctypes
import fcntl
import os
import struct
import sys

MFI_CMD_PD_SCSI_IO = 0x04
MFI_FRAME_DIR_READ = 0x0010
IOCPACKET_SIZE = 2 + 2 + 4 + 4 + 4 + 4 + 128 + 16 * 16
MEGASAS_IOC_FIRMWARE = (3 << 30) | (IOCPACKET_SIZE << 16) | (ord('M') << 8) | 1


def pd_scsi(host_no, dev_id, cdb, xfer_len, timeout=30):
    data = ctypes.create_string_buffer(max(xfer_len, 1))
    sense = ctypes.create_string_buffer(96)
    frame = bytearray(128)
    frame[0] = MFI_CMD_PD_SCSI_IO
    frame[4] = dev_id
    frame[5] = 0
    frame[6] = len(cdb)
    frame[7] = 1 if xfer_len else 0
    struct.pack_into('<H', frame, 16, MFI_FRAME_DIR_READ if xfer_len else 0)
    struct.pack_into('<H', frame, 18, timeout)
    struct.pack_into('<I', frame, 20, xfer_len)
    struct.pack_into('<Q', frame, 24, ctypes.addressof(sense))  # sense_off holds a user pointer
    frame[32:32 + len(cdb)] = cdb
    pkt = bytearray(IOCPACKET_SIZE)
    struct.pack_into('<HHIIII', pkt, 0, host_no, 0, 48, 1 if xfer_len else 0, 24, 32)
    pkt[20:148] = frame
    if xfer_len:
        struct.pack_into('<QQ', pkt, 148, ctypes.addressof(data), xfer_len)
    fd = os.open('/dev/megaraid_sas_ioctl_node', os.O_RDWR)
    try:
        fcntl.ioctl(fd, MEGASAS_IOC_FIRMWARE, pkt, True)
    finally:
        os.close(fd)
    cmd_status, scsi_status = pkt[20 + 2], pkt[20 + 3]
    return cmd_status, scsi_status, data.raw[:xfer_len], sense.raw[:32]


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    host, dev, op = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    if op == 'inquiry':
        st, ss, d, sn = pd_scsi(host, dev, bytes([0x12, 0, 0, 0, 96, 0]), 96)
        print(f'cmd_status=0x{st:02x} scsi_status=0x{ss:02x}')
        print(f'type=0x{d[0]:02x} vendor={d[8:16]!r} product={d[16:32]!r} rev={d[32:36]!r}')
    elif op == 'cap':
        cdb = bytes([0x9e, 0x10]) + bytes(8) + struct.pack('>I', 32) + bytes(2)
        st, ss, d, sn = pd_scsi(host, dev, cdb, 32)
        lba, bs = struct.unpack('>QI', d[:12])
        print(f'cmd_status=0x{st:02x} scsi_status=0x{ss:02x} last_lba=0x{lba:x} block_size={bs}')
    elif op == 'read':
        lba = int(sys.argv[4], 0)
        n = int(sys.argv[5]) if len(sys.argv) > 5 else 1
        cdb = bytes([0x88, 0]) + struct.pack('>Q', lba) + struct.pack('>I', n) + bytes(2)
        st, ss, d, sn = pd_scsi(host, dev, cdb, 512 * n)
        print(f'cmd_status=0x{st:02x} scsi_status=0x{ss:02x} sense={sn[:18].hex()}')
        sys.stdout.flush()
        if len(sys.argv) > 6:
            open(sys.argv[6], 'wb').write(d)
        else:
            for i in range(0, min(len(d), 512), 32):
                print(f'{i:04x}: {d[i:i+32].hex()}')
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
