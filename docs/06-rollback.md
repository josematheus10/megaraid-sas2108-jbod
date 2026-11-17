# 6. Rollback

## Back to the stock driver

```sh
rm /etc/modprobe.d/megaraid-jbod.conf
dkms remove megaraid_sas/07.734.00.00-jbod1 --all
update-initramfs -u -k all
reboot
```

The raw disks disappear; virtual drives keep working. Nothing on the disks is changed. To keep the
patched module installed but inactive, only remove `megaraid-jbod.conf` (or set
`expose_ugood_pds=0`) and reboot.

## Back to virtual drives, keeping the data (one disk per VD)

Creating a RAID0 VD over a raw disk writes DDF metadata at the end of the disk; in the test
(`MegaCli64 -CfgLdAdd -r0[...]`, no init option) only that end area was overwritten. Data written
as a raw disk is then at LBA 0 of the VD, but the VD is shorter than the disk: on the tested 500 GB
disk the VD lost 1,073,200 sectors (~524 MiB) at the end, and anything stored there is gone.
Shrink the filesystem/partition first if needed, and never run fast/full initialisation on the new
VD. Only the opposite direction (VD → raw) was verified with checksums.

## Back to the LSI firmware

See [`01-firmware.md` §1.5](01-firmware.md#15-going-back-to-the-lsi-image-not-tested): flash LSI
12.15.0-0239 (`mr2108fw.rom`, SHA-256 `fae2d66c…fb4d`) with StorCLI, then reboot the host.
