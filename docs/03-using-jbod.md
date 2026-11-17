# 3. Using the raw disks

Rule: **a disk is exposed to the OS if, and only if, the controller reports it as
Unconfigured Good (UGood)**. Members of virtual drives (Online), hot spares, Unconfigured Bad and
other states are never exposed.

Enclosure/slot examples below use `252:4`; get yours with `storcli64 /c0/eall/sall show`.

## 3.1 See what the controller and the OS see

```sh
storcli64 /c0/eall/sall show      # State column: UGood / Onln / UBad ...
./tools/jbod-status.sh            # raw disks = channel 0 in HCTL (6:0:4:0), VDs = channel 2
```

Raw disks look like plain SATA/SAS disks: real model, serial, WWN, full capacity and
`smartctl -a /dev/sdX` without `-d megaraid,N`. `/dev/disk/by-id/wwn-*` links are the disk's own.

## 3.2 New or empty disk

A disk that never belonged to an array is normally UGood already and shows up as soon as it is
inserted (the driver reacts to the controller's events).

If it is **Unconfigured Bad** (for example after a timeout), mark it good. This changes only the
controller state, not the data:

```sh
storcli64 /c0/e252/s4 set good force
# or
MegaCli64 -PDMakeGood -PhysDrv[252:4] -Force -a0
```

## 3.3 Existing single-disk RAID0 virtual drive → raw disk, keeping the data

On the SAS2108 a one-disk RAID0 stores the data from LBA 0 of the disk and keeps its DDF metadata
at the end. Deleting the VD **without initialising it** leaves the data where it is:

```sh
storcli64 /c0/v3 show                   # confirm: RAID0, exactly one drive
MegaCli64 -CfgLdDel -L3 -a0             # deletes only the configuration
```

The disk becomes UGood and appears as `/dev/sdX` within seconds.

Tested: ext4 + 200 files + 300 MB of random data on a VD; after `CfgLdDel` the raw disk had the
same SHA-256 over the first 512 MiB, `fsck` was clean and 202/202 files matched.

Notes:

- Only for **single-disk RAID0**. Multi-disk stripes/mirrors/parity sets are not readable from one
  member.
- The raw disk is slightly larger than the VD was (the DDF area at the end becomes visible). A GPT
  written on the VD has its backup header at the VD's end, not the disk's; `sgdisk -e /dev/sdX`
  moves it. The old DDF anchor stays at the end of the disk, so `blkid` may report
  `ddf_raid_member` until something overwrites it.
- Never run "initialize"/"fast init" on a VD whose data you want to keep.

## 3.4 Turning a raw disk back into a VD

Creating a VD on a raw disk (`MegaCli64 -CfgLdAdd -r0[252:7] -a0`, the command used in the test,
or `storcli64 /c0 add vd type=raid0 drives=252:7`) removes the raw `/dev/sdX`
immediately and exposes the VD instead; the same disk is never visible twice. Creating a VD writes
DDF metadata at the end of the disk, which overwrites whatever was there (ZFS detected and repaired
it in the test). Deleting the VD later brings the raw disk back.

The controller refuses to create a VD on a disk that carries a foreign configuration (error 0x26),
so a raw disk with foreign metadata cannot be grabbed by mistake. Importing/clearing foreign
configurations was not tested with the patched driver.

## 3.5 Removing a disk

`storcli`/`MegaCli` "prepare for removal" (`PdPrpRmv`) does not detach the disk: it spins up again
on the next I/O. Remove it from the OS first:

```sh
echo 1 > /sys/block/sdX/device/delete
```

then pull it. Physical hot-swap was not tested; removal/re-add via the SCSI layer was (see
[`05-test-results.md`](05-test-results.md)).

## 3.6 Things that are different from a real HBA

- Spin-down: the controller does not stop the motors on request from the host.
- Booting from a raw disk: not tested; the controller's option ROM only presents virtual drives.
- The card's management tools still list the disks as UGood; nothing in the controller marks them
  as "in use". Do not run `CfgLdAdd`/`add vd` on disks you use as raw disks.
