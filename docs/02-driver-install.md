# 2. Installing the patched `megaraid_sas` driver

The driver is the upstream Linux `megaraid_sas` with one extra module parameter,
`expose_ugood_pds`. With the parameter off (default) it behaves exactly like the stock driver.
It is installed with DKMS, so it is rebuilt automatically for new kernels and the distribution's
module stays untouched.

Tested on Proxmox VE 9.2 (Debian 13), kernel `7.0.2-6-pve`, driver `07.734.00.00-rc1`.

## 2.1 Prerequisites

```sh
apt install dkms build-essential python3 curl
apt install proxmox-headers-$(uname -r)     # Proxmox VE
# or: apt install linux-headers-$(uname -r) # Debian / Ubuntu
```

If the card is currently passed through to a VM (`vfio-pci ids=1000:0079` in `/etc/modprobe.d/`,
`hostpci` in the VM config), remove that first: the host must own the card.

## 2.2 Get a source tree that matches your kernel

**Option A: kernel 6.17 – 7.x (driver 07.734.00.00).** Use the tree shipped in this repository,
which is the one running on the test machine:

```sh
cp -r driver/dkms /usr/src/megaraid_sas-07.734.00.00-jbod1
```

**Option B: any other kernel.** Generate the tree from the upstream source of your kernel version:

```sh
./driver/make-dkms-source.sh              # uses v<major>.<minor> of the running kernel
./driver/make-dkms-source.sh v6.8         # or name the tag explicitly
```

The script downloads `drivers/scsi/megaraid/` for that tag from the `torvalds/linux` GitHub mirror,
applies `patch_expose_ugood.py` and writes `/usr/src/megaraid_sas-<version>-jbod1/`. The patch
applies unchanged to upstream v5.4, 5.10, 5.15, 6.1, 6.6, 6.8, 6.12, 6.14, 6.17, 7.0 and current
master. Only the 7.0 build has been compiled and run; distribution kernels with backported driver
changes may need the distribution's own source instead (apply `driver/expose_ugood_pds.patch` or
the Python script to it).

## 2.3 Build and install

```sh
dkms install megaraid_sas/07.734.00.00-jbod1     # use the version printed in step 2.2
modinfo -n megaraid_sas
# must print .../updates/dkms/megaraid_sas.ko
modinfo -p megaraid_sas | grep expose_ugood_pds
```

## 2.4 Turn the feature on

```sh
echo "options megaraid_sas expose_ugood_pds=1" > /etc/modprobe.d/megaraid-jbod.conf
update-initramfs -u -k all
```

## 2.5 Load it

If nothing on the controller is in use (no mounted filesystem, no VM disk, no pool on its virtual
drives), reload the module:

```sh
modprobe -r megaraid_sas && modprobe megaraid_sas
```

Otherwise reboot. Check:

```sh
cat /sys/module/megaraid_sas/parameters/expose_ugood_pds    # Y
dmesg | grep expose_ugood_pds
# megaraid_sas 0000:03:00.0: expose_ugood_pds: PD 4 (UGood) exposed as pass-through disk
./tools/jbod-status.sh
```

## 2.6 Kernel updates

DKMS rebuilds the module for each new kernel. If the build fails (kernel API change), the stock
driver is loaded instead: the raw disks disappear and only virtual drives are visible. Nothing is
written to the disks in that case. Regenerate the tree for the new kernel with
`make-dkms-source.sh` and install it.

## 2.7 Uninstall

```sh
rm /etc/modprobe.d/megaraid-jbod.conf
dkms remove megaraid_sas/07.734.00.00-jbod1 --all
update-initramfs -u -k all
reboot
```
