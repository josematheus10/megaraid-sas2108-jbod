#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Build a DKMS source tree of megaraid_sas + expose_ugood_pds for a given
# upstream kernel tag, downloaded from the torvalds/linux GitHub mirror.
#
# Usage: make-dkms-source.sh [kernel-tag] [destination-parent]
#   kernel-tag          default: v<major>.<minor> of the running kernel (e.g. v6.8)
#   destination-parent  default: /usr/src
#
# Result: <destination-parent>/megaraid_sas-<driver-version>-jbod1/
# Then:   dkms install megaraid_sas/<driver-version>-jbod1
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
tag=${1:-v$(uname -r | cut -d. -f1-2)}
parent=${2:-/usr/src}
base="https://raw.githubusercontent.com/torvalds/linux/$tag/drivers/scsi/megaraid"

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

echo "== downloading drivers/scsi/megaraid from $tag"
curl -fsSL "$base/Makefile" -o "$work/Makefile"
objs=$(sed -e ':a' -e '/\\$/N; s/\\\n//; ta' "$work/Makefile" |
       sed -n 's/^megaraid_sas-objs[[:space:]]*:=[[:space:]]*//p' | tr -s '[:space:]' ' ')
[ -n "$objs" ] || { echo "megaraid_sas-objs not found in upstream Makefile" >&2; exit 1; }
for o in $objs; do
    curl -fsSL "$base/${o%.o}.c" -o "$work/${o%.o}.c"
done
for h in megaraid_sas.h megaraid_sas_fusion.h; do
    curl -fsSL "$base/$h" -o "$work/$h"
done

ver=$(sed -n 's/^#define MEGASAS_VERSION[[:space:]]*"\(.*\)"/\1/p' "$work/megaraid_sas.h")
ver=${ver%-rc*}
pkgver="$ver-jbod1"
dest="$parent/megaraid_sas-$pkgver"

echo "== applying expose_ugood_pds (driver $ver)"
python3 "$here/patch_expose_ugood.py" "$work/megaraid_sas_base.c"

[ -e "$dest" ] && { echo "$dest already exists, remove it first" >&2; exit 1; }
mkdir -p "$dest"
cp "$work"/*.c "$work"/*.h "$dest/"
printf 'obj-m := megaraid_sas.o\nmegaraid_sas-objs := %s\n' "$objs" > "$dest/Kbuild"
cat > "$dest/dkms.conf" <<EOF
PACKAGE_NAME="megaraid_sas"
PACKAGE_VERSION="$pkgver"
BUILT_MODULE_NAME[0]="megaraid_sas"
DEST_MODULE_LOCATION[0]="/updates/dkms"
MAKE[0]="make -C \${kernel_source_dir} M=\${dkms_tree}/\${PACKAGE_NAME}/\${PACKAGE_VERSION}/build modules"
CLEAN="make -C \${kernel_source_dir} M=\${dkms_tree}/\${PACKAGE_NAME}/\${PACKAGE_VERSION}/build clean"
AUTOINSTALL="yes"
EOF
echo "== created $dest"
echo "next: dkms install megaraid_sas/$pkgver"
