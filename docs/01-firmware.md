# 1. Firmware: step by step

This is the exact path the test card went through:

```
12.0.1-0102 (factory)  →  LSI 12.12.0-0048  →  LSI 12.15.0-0239  →  IBM 12.15.0-0248 (running now)
```

> **The JBOD patch does not depend on the IBM firmware.** No firmware build for the SAS2108 enables
> firmware JBOD on a 9264-8i (`Support JBOD = No` on both 12.15 builds). The patch was developed and
> tested while the card ran IBM 12.15.0-0248, so that is the combination documented as working.
> It should also work on LSI 12.15.0-0239, which accepts the same pass-through command, but that
> combination was **not tested**.

Flashing firmware can brick the card. Do not power off during a flash, keep the controller cache
empty (no pending writes, no BBU-preserved cache) and have a backup of the data on the disks.

## 1.0 Tools

- `storcli64`: Broadcom StorCLI. The IBM package below contains `storcli64` 1.18.08, which is the
  one used for the IBM flash. Any StorCLI that sees the card works for the LSI images.
- `MegaCli64` 8.07.14 (optional, used for backups and some PD commands). Link in
  [`firmware/README.md`](../firmware/README.md). On recent distros it needs `libncurses5`/`libtinfo5`
  (or symlinks of `libncurses.so.5`/`libtinfo.so.5` to the version 6 libraries).
- Download and verify all images with `firmware/fetch-firmware.sh`.

## 1.1 Back up the controller state

```sh
storcli64 /c0 show all            > c0-show-all.txt
storcli64 /c0/eall/sall show all  > c0-drives.txt
MegaCli64 -AdpAllInfo -a0 -NoLog  > adpallinfo.txt
MegaCli64 -CfgSave -f megaraid-config.bin -a0 -NoLog   # VD layout, restorable with -CfgRestore
```

Write down the **SAS address** of the card (`storcli64 /c0 show all | grep -i "SAS Address"`).

Check the current version:

```sh
storcli64 /c0 show | grep -E "FW Package Build|FW Version|BIOS Version"
```

## 1.2 From 12.0.x: go through 12.12.0-0048 first

A direct jump from 12.0.1-0102 to 12.15 is refused by the controller ("image is corrupted"; also
reported publicly by another 9264-8i owner). Flash 12.12 first:

```sh
storcli64 /c0 download file=fw/lsi-12.12.0-0048/mr2108fw.rom
```

Then power-cycle or reboot the host. On the test machine (card passed through to a VM at the time)
12.12 became active after restarting the VM.

## 1.3 LSI 12.15.0-0239 (last LSI build, the fallback image)

```sh
storcli64 /c0 download file=fw/lsi-12.15.0-0239/mr2108fw.rom
```

12.15 stayed *pending* after two VM restarts and only became active after a **full reboot of the
host**. Plan for a real reboot.

Expected afterwards:

```
FW Package Build = 12.15.0-0239
FW Version       = 2.130.403-4660
BIOS Version     = 3.30.02.2_4.16.08.00
```

## 1.4 IBM ServeRAID M5000 12.15.0-0248 (what the card runs now)

Same BIOS/WebBIOS/NVDATA as the LSI 12.15 image, newer firmware application (2.130.403-6221). It
was tried because IBM's change log mentions "JBOD mode"; on the 9264-8i it did **not** enable
firmware JBOD (the JBOD capability comes from the card identity/NVDATA, not from the build).

1. Extract the package. The `.bin` is a 32-bit self-extractor with a ZIP appended, so any ZIP
   reader works (`fetch-firmware.sh` does this). Running the self-extractor with
   `-x ibm-12.15.0-0248` also works where a 32-bit loader is installed (`libc6-i386`).

   ```sh
   python3 -c 'import zipfile; zipfile.ZipFile("ibm_fw_sraidmr_m5000-12.15.0-0248_linux_32-64.bin").extractall("ibm-12.15.0-0248")'
   sha256sum ibm-12.15.0-0248/image/m5000fw.rom
   # 680c66689551a2751086c30cfa6bc39ee5fc6619c62286ccf77485fc74956d53
   ```

2. Flash with the StorCLI shipped in the package. It accepted the LSI-branded 9264-8i without any
   force option:

   ```sh
   cd ibm-12.15.0-0248/image
   chmod +x storcli64          # the ZIP extraction does not keep the exec bit
   ./storcli64 /c0 download file=m5000fw.rom
   ```

3. Reboot the host and check:

   ```
   FW Package Build = 12.15.0-0248
   FW Version       = 2.130.403-6221
   ```

The card keeps its LSI identity (`1000:0079`, subsystem `1000:9264`); virtual drives and disks were
untouched by the flash.

## 1.5 Going back to the LSI image (not tested)

Flashing the LSI 12.15.0-0239 image over IBM 12.15.0-0248 should be:

```sh
storcli64 /c0 download file=fw/lsi-12.15.0-0239/mr2108fw.rom
# if StorCLI refuses because the package number is lower:
storcli64 /c0 download file=fw/lsi-12.15.0-0239/mr2108fw.rom noverchk
```

followed by a host reboot. This was **not** performed on the test card; it is documented so that
the fallback image is at hand.

## 1.6 What not to do

See [`07-dead-ends.md`](07-dead-ends.md): there is no IT firmware for the SAS2108, `lsirec` and
`megarec` can fault or wipe the card, and changing the SBR identity does not stick.
