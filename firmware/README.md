# Firmware files

The firmware images are **not** stored in this repository (they are Broadcom and IBM property).
`fetch-firmware.sh` downloads them from the vendors' own servers and checks every file against
[`SHA256SUMS`](SHA256SUMS). Nothing is flashed by that script.

```sh
./firmware/fetch-firmware.sh /tmp/fw     # downloads, extracts and verifies
```

## Files

| Role | Package | Image inside | Download |
|---|---|---|---|
| **Running now** (patch tested on this one) | IBM ServeRAID M5000 **12.15.0-0248**, FW 2.130.403-6221 | `image/m5000fw.rom` | [ibm_fw_sraidmr_m5000-12.15.0-0248_linux_32-64.bin](https://download2.boulder.ibm.com/sar/CMA/XSA/06fl9/1/ibm_fw_sraidmr_m5000-12.15.0-0248_linux_32-64.bin) |
| **Fallback / original LSI image** (last LSI build for SAS2108) | LSI MegaRAID **12.15.0-0239**, FW 2.130.403-4660 (10/2015) | `mr2108fw.rom` | [12.15.0-0239_MR_2108_SAS_FW_2.130.403-4660.zip](https://docs.broadcom.com/docs-and-downloads/docs-and-downloads/raid-controllers/raid-controllers-common-files/12.15.0-0239_MR_2108_SAS_FW_2.130.403-4660.zip) |
| Intermediate step (needed from 12.0.x) | LSI MegaRAID **12.12.0-0048**, FW 2.120.63-1242 | `mr2108fw.rom` | [12-12-0-0048_SAS_2108_FW_Image_APP-2-120-63-1242.zip](https://docs.broadcom.com/docs-and-downloads/raid-controllers/raid-controllers-common-files/12-12-0-0048_SAS_2108_FW_Image_APP-2-120-63-1242.zip) |
| Management tool | MegaCLI 8.07.14 | `Linux/MegaCli-8.07.14-1.noarch.rpm` | [8-07-14_MegaCLI.zip](https://docs.broadcom.com/docs-and-downloads/raid-controllers/raid-controllers-common-files/8-07-14_MegaCLI.zip) |

SHA-256 of the images that were actually flashed:

| Image | SHA-256 |
|---|---|
| IBM 12.15.0-0248 `m5000fw.rom` | `680c66689551a2751086c30cfa6bc39ee5fc6619c62286ccf77485fc74956d53` |
| LSI 12.15.0-0239 `mr2108fw.rom` | `fae2d66c1a59af46f1018cd285ac388179994acd501d405a3835dc12f19ffb4d` |
| LSI 12.12.0-0048 `mr2108fw.rom` | `2c06615d898021bfdb0185d852d696d20b8b05264e61fef103c832b0014ac789` |

Notes:

- The 9264-8i is not listed in the LSI release notes, but it uses the 9260-8i image (`mr2108fw.rom`).
- Both 12.15 images are 4,980,736 bytes and carry the same BIOS (3.30.02.2_4.16.08.00), WebBIOS
  (6.0-54-e_50) and NVDATA (2.09.03-0058); only the firmware application differs (6221 vs 4660).
- The card shipped with package 12.0.1-0102 (FW 2.0.83-1327). That image was not dumped before the
  update, so it is not available here.
- The 12.15.0-0239 LSI file was downloaded on 2026-11-17 from the link above and matched the
  SHA-256 of the copy kept as the project's fallback image.
- Broadcom pages: the 12.15.0-0239 package is listed under *Legacy Products → MegaRAID SAS 9260-8i →
  Firmware* on the Broadcom support download search.

Step-by-step flashing instructions: [`docs/01-firmware.md`](../docs/01-firmware.md).
