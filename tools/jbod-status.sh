#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Show whether the patched megaraid_sas is active and which disks it exposes.
# Read-only. If storcli64 or MegaCli64 is in PATH, the controller's view of
# the drives is printed too.
set -u

ok=0; fail=0
check() {
    if eval "$2" >/dev/null 2>&1; then echo "OK    $1"; ok=$((ok + 1))
    else echo "FAIL  $1"; fail=$((fail + 1)); fi
}

check "megaraid_sas module loaded"  'grep -q "^megaraid_sas " /proc/modules'
check "module has expose_ugood_pds" '[ -e /sys/module/megaraid_sas/parameters/expose_ugood_pds ]'
check "expose_ugood_pds=Y"          '[ "$(cat /sys/module/megaraid_sas/parameters/expose_ugood_pds)" = Y ]'
echo "      module file: $(modinfo -n megaraid_sas 2>/dev/null)"

echo
echo "== block devices behind megaraid_sas"
for host in /sys/class/scsi_host/host*; do
    [ "$(cat "$host/proc_name" 2>/dev/null)" = megaraid_sas ] || continue
    h=${host##*host}
    pci=$(basename "$(dirname "$(readlink -f "$host/device")")")
    echo "-- SCSI host $h (PCI $pci)"
    lsblk -dnro NAME,HCTL,SIZE,MODEL | while read -r name hctl size model; do
        IFS=: read -r hh ch _ _ <<<"$hctl"
        [ "$hh" = "$h" ] || continue
        if [ "$ch" = 2 ]; then kind="virtual drive"; else kind="raw disk (pass-through)"; fi
        printf "   %-8s %-10s %-8s %-26s %s\n" "$name" "$hctl" "$size" "$(printf '%b' "$model")" "$kind"
    done
done
echo "   (channel 2 = virtual drives; other channels = physical disks exposed by the patch)"

echo
if command -v storcli64 >/dev/null 2>&1; then
    echo "== controller view (storcli64 /c0/eall/sall show)"
    storcli64 /c0/eall/sall show | grep -E '^[0-9]+:[0-9]+ '
elif command -v MegaCli64 >/dev/null 2>&1; then
    echo "== controller view (MegaCli64 -PDList)"
    MegaCli64 -PDList -aALL -NoLog | grep -E 'Slot Number|Firmware state'
fi

echo
dmesg 2>/dev/null | grep 'expose_ugood_pds' | tail -n 10
echo "== $ok OK, $fail FAIL"
[ "$fail" = 0 ]
