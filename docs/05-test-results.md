# 5. Test results

Machine: LSI MegaRAID SAS 9264-8i (`1000:0079`, subsystem `1000:9264`, 256 MB cache, no BBU) on an
Intel X58 board, Proxmox VE 9.2, kernel `7.0.2-6-pve`, firmware IBM 12.15.0-0248. Disks: WD
WD1001FALS 1 TB, WD WD5003AZEX 500 GB (×2), WD WD5001AALS 500 GB (×2), later also a Toshiba
MQ01ABD100 1 TB and a SATA SSD. All SATA, through the card's two SFF-8087 ports.

## Single disk, first run (Unconfigured Good, no VD)

| Check | Result |
|---|---|
| Device | `/dev/sdd`, HCTL `6:0:4:0` (physical channel; VDs live on channel 2) |
| Identity | real model, serial and WWN of the disk (not of the controller) |
| Capacity | 976,773,168 sectors = whole disk (the RAID0 VD on it had 975,699,968); 4096-byte physical blocks reported |
| SMART | `smartctl -a /dev/sdd` directly, no `-d megaraid` |
| Read | 2 GiB `O_DIRECT` at **162 MB/s**; the old DDF anchor (`de11de11`) in the last LBA reads the same through `/dev/sdd` and through `mfi_pt.py` |
| Write | 1 MiB random written, read back identical, original content restored and verified; 256 MiB at **158 MB/s**, restored and verified |
| Media error | read over a region with pending sectors: the kernel got `Medium Error / Unrecovered read error` with the exact LBA in ~2 s; the disk stayed `running` and **UGood**. With the same disk as a RAID0 VD, the same error made the controller mark it FAILED and take the VD offline |
| Existing metadata | `blkid` shows the `ddf_raid_member` signature already on the disk: content is delivered raw |

## Data preservation (VD → raw)

ext4 + 300 MB random data + 200 files on a single-disk RAID0 VD → `MegaCli64 -CfgLdDel` (no init) →
raw disk: SHA-256 of the first 512 MiB identical, `fsck` clean, 202/202 files verified.

## Five disks, before using them for real data

| Test | How | Result |
|---|---|---|
| ZFS | raidz1 over 5 raw disks, 8 GiB random data, scrub | 0 errors; SMART read directly from all 5 |
| Silent corruption | 1 GiB random written behind ZFS's back into one disk's data area | 1.87k checksum errors detected, 59.9 MB repaired, file intact, next scrub clean |
| Controller "prepare for removal" | `PdPrpRmv` | does not detach: the disk spins up on the next command, ZFS notices nothing |
| OS-level removal / hot-plug | `echo 1 > .../device/delete` during writes, then SCSI host rescan | pool DEGRADED, write completed; disk came back with the same name, automatic resilver of 513 MB in 5 s |
| Bad sectors on 2 disks at once | read across a bad region on one disk and the end of another | 131 sectors `Medium Error` at ~2 s each, **no timeout, reset or OCR**, disks stay running/UGood, pool unaffected |
| UGood → VD member | `CfgLdAdd -r0[252:7]` with the pool in use | raw disk vanished, only the VD appeared; forced rescan did not re-expose it (never exposed twice); after deleting the VD the raw disk returned, resilver, scrub clean. Creating the VD wrote DDF metadata at the end of the disk (ZFS repaired it) |
| Disk with foreign config | `CfgLdAdd` on it | controller refuses (0x26) |
| Module reload | `modprobe -r` / `modprobe` ×3 | all disks back each time, DKMS module |
| Host reboot | `systemctl reboot` | disks present after boot |
| Full power-off | `poweroff` + Wake-on-LAN | back in ~110 s, 20/20 post-boot checks passed |

## Long-running use

Since 2026-11-12 the card runs only raw disks (0 virtual drives) on this driver, holding an LVM
volume exported over iSCSI and a mergerfs pool of ext4 disks. State on 2026-11-17, after 1.5 days
since the last boot:

```
megaraid_sas 0000:03:00.0: Secure JBOD support        : No
megaraid_sas 0000:03:00.0: expose_ugood_pds: PD 0 (UGood) exposed as pass-through disk
megaraid_sas 0000:03:00.0: expose_ugood_pds: PD 1 (UGood) exposed as pass-through disk
megaraid_sas 0000:03:00.0: expose_ugood_pds: PD 2 (UGood) exposed as pass-through disk
megaraid_sas 0000:03:00.0: expose_ugood_pds: PD 4 (UGood) exposed as pass-through disk
megaraid_sas 0000:03:00.0: expose_ugood_pds: PD 5 (UGood) exposed as pass-through disk
megaraid_sas 0000:03:00.0: expose_ugood_pds: PD 7 (UGood) exposed as pass-through disk
```

One old 500 GB disk dropped out during this period (command timeouts). Swapping data cables showed
the fault follows that drive (its power connector was also suspect), not the driver or the
controller; the other disks kept working.

## Not tested yet

- Physical hot-swap of a disk while the system runs.
- LSI firmware 12.15.0-0239 with the patched driver (developed on IBM 12.15.0-0248).
- Kernels other than 7.0 (the patch applies textually to v5.4–7.0, see `02-driver-install.md`).
- Other SAS2108 cards, SAS disks, expanders, SSD TRIM behaviour.
- Booting from a raw disk.
