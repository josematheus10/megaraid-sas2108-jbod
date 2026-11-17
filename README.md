# JBOD / pass-through for LSI MegaRAID SAS 9264-8i (SAS2108)

Real raw-disk access on a **MegaRAID SAS 9264-8i** — a card whose firmware has no JBOD mode and for
which no IT firmware exists — through a small patch to the Linux `megaraid_sas` driver.

With `expose_ugood_pds=1`, every disk the controller reports as **Unconfigured Good** shows up in
Linux as a normal `/dev/sdX`: the disk's own model, serial, WWN and full capacity, SMART with plain
`smartctl`, media errors passed to the OS instead of the controller dropping the disk. Existing data
on the disk is delivered as-is. Virtual drives keep working next to the raw disks.

```
$ dmesg | grep expose_ugood
megaraid_sas 0000:03:00.0: expose_ugood_pds: PD 4 (UGood) exposed as pass-through disk
$ lsblk -do NAME,HCTL,SIZE,MODEL /dev/sde
NAME HCTL      SIZE MODEL
sde  6:0:4:0 465.8G WDC WD5003AZEX-00K1GA0
```

## Status

| | |
|---|---|
| Card | LSI MegaRAID SAS 9264-8i, `1000:0079` / subsystem `1000:9264` |
| Firmware running | IBM ServeRAID M5000 **12.15.0-0248** (FW 2.130.403-6221) |
| Fallback firmware | LSI **12.15.0-0239** (FW 2.130.403-4660), last LSI build for SAS2108 |
| Driver | `megaraid_sas` 07.734.00.00 + `expose_ugood_pds`, DKMS |
| Tested on | Proxmox VE 9.2, kernel 7.0.2-6-pve, SATA disks |
| In use since | 2026-11-12, only raw disks on the card (ZFS, LVM/iSCSI and ext4/mergerfs tested) |

It works because the SAS2108 firmware executes `MFI_CMD_PD_SCSI_IO` (SCSI pass-through to a physical
disk) for normal READ/WRITE commands, and the driver already has an I/O path for pass-through
disks. The firmware just never lists any disk for it. Details:
[`docs/04-how-it-works.md`](docs/04-how-it-works.md).

## Quick start (Debian / Proxmox, kernel 6.17–7.x)

```sh
git clone https://github.com/josematheus10/megaraid-sas2108-jbod
cd megaraid-sas2108-jbod
apt install dkms build-essential proxmox-headers-$(uname -r)    # or linux-headers-$(uname -r)

cp -r driver/dkms /usr/src/megaraid_sas-07.734.00.00-jbod1
dkms install megaraid_sas/07.734.00.00-jbod1
echo "options megaraid_sas expose_ugood_pds=1" > /etc/modprobe.d/megaraid-jbod.conf
update-initramfs -u -k all
reboot

./tools/jbod-status.sh
```

Other kernels: `./driver/make-dkms-source.sh` builds the DKMS tree from the upstream source of your
kernel version (the patch applies to v5.4 through v7.0).

## Documentation

1. [Firmware: step by step](docs/01-firmware.md) — backup, 12.0 → 12.12 → 12.15 LSI → IBM 12.15.0-0248
2. [Installing the driver](docs/02-driver-install.md)
3. [Using the raw disks](docs/03-using-jbod.md) — UGood, converting a RAID0 VD to a raw disk without losing data
4. [How it works](docs/04-how-it-works.md)
5. [Test results](docs/05-test-results.md)
6. [Rollback](docs/06-rollback.md)
7. [What did not work](docs/07-dead-ends.md) — IT firmware, IBM crossflash, `lsirec`/`megarec` hazards

## Repository layout

```
driver/
  expose_ugood_pds.patch    patch against drivers/scsi/megaraid/megaraid_sas_base.c (v7.0)
  patch_expose_ugood.py     same change as a script; works on upstream v5.4 – v7.0
  make-dkms-source.sh       download upstream driver for a kernel tag, patch, create DKMS tree
  dkms/                     ready DKMS tree (driver 07.734.00.00, running on the test machine)
tools/
  jbod-status.sh            read-only status: module, parameter, raw disks vs VDs
  mfi_pt.py                 read-only pass-through test via the management ioctl (stock driver)
firmware/
  README.md, SHA256SUMS     official download links and checksums (binaries are not included)
  fetch-firmware.sh         download + verify + extract, never flashes
docs/                       step-by-step guides
```

## Warnings

- This is a hobby/homelab project, not supported by Broadcom, IBM or the kernel maintainers.
- The controller still believes the raw disks are unused (UGood). Creating a virtual drive on one
  of them takes it away from the OS and overwrites its last sectors.
- Firmware flashing can brick the card. Keep backups of the data on your disks.
- Only the 9264-8i was tested. Other SAS2108 cards (9260, 9261, 9280, PERC H700/H800,
  ServeRAID M5014/M5015, …) run the same firmware family and should behave the same way.

## License

The driver sources and patch are derived from the Linux kernel `megaraid_sas` driver and are
GPL-2.0-or-later, like the original. The scripts in this repository are GPL-2.0-or-later as well.
See [`LICENSE`](LICENSE). Firmware images are property of Broadcom and IBM and are not
redistributed here.
