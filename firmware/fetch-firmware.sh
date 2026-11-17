#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Download the firmware packages used in this project from the vendors'
# servers, verify them against SHA256SUMS and extract the flashable images.
# Nothing is flashed. The binaries are not redistributed in this repository.
#
# Usage: fetch-firmware.sh [output-dir]      (default: ./fw)
# Needs: curl, sha256sum, python3 (zip extraction).
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
out=${1:-fw}
mkdir -p "$out"
cd "$out"

BC=https://docs.broadcom.com/docs-and-downloads
get() {
    [ -s "$2" ] || { echo "== downloading $2"; curl -fL --retry 3 -o "$2.part" "$1" && mv "$2.part" "$2"; }
}
get "$BC/raid-controllers/raid-controllers-common-files/12-12-0-0048_SAS_2108_FW_Image_APP-2-120-63-1242.zip" \
    12-12-0-0048_SAS_2108_FW_Image_APP-2-120-63-1242.zip
get "$BC/docs-and-downloads/raid-controllers/raid-controllers-common-files/12.15.0-0239_MR_2108_SAS_FW_2.130.403-4660.zip" \
    12.15.0-0239_MR_2108_SAS_FW_2.130.403-4660.zip
get "https://download2.boulder.ibm.com/sar/CMA/XSA/06fl9/1/ibm_fw_sraidmr_m5000-12.15.0-0248_linux_32-64.bin" \
    ibm_fw_sraidmr_m5000-12.15.0-0248_linux_32-64.bin
get "$BC/raid-controllers/raid-controllers-common-files/8-07-14_MegaCLI.zip" \
    8-07-14_MegaCLI.zip

unzip_to() {
    python3 -c 'import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])' "$1" "$2"
}
[ -d lsi-12.12.0-0048 ] || unzip_to 12-12-0-0048_SAS_2108_FW_Image_APP-2-120-63-1242.zip lsi-12.12.0-0048
[ -d lsi-12.15.0-0239 ] || unzip_to 12.15.0-0239_MR_2108_SAS_FW_2.130.403-4660.zip lsi-12.15.0-0239
# the IBM .bin is a 32-bit self-extractor with a ZIP appended; read the ZIP directly
[ -d ibm-12.15.0-0248 ] || unzip_to ibm_fw_sraidmr_m5000-12.15.0-0248_linux_32-64.bin ibm-12.15.0-0248

echo "== verifying"
sha256sum -c "$here/SHA256SUMS"
