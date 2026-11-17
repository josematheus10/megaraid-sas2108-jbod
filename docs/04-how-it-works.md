# 4. How it works

## The firmware side

The SAS2108 runs MegaRAID (MFI) firmware. It has no IT/HBA personality and, on the 9264-8i, no
firmware JBOD:

| Check | Result |
|---|---|
| `storcli64 /c0 set jbod=on` | `Controller does not support JBOD` |
| `MegaCli64 -AdpSetProp EnableJBOD 1 -a0` | `Failed to Set Adapter Properties` |
| `Support JBOD` / `Enable JBOD` (`storcli /c0 show all`, `-AdpAllInfo`) | `No` / `No`, on LSI 12.15.0-0239 and IBM 12.15.0-0248 |
| `Support Force Personality Change` | `No` |
| Driver log | `Secure JBOD support : No`, `JBOD sequence map support : No` |

What the firmware **does** accept is `MFI_CMD_PD_SCSI_IO` (opcode `0x04`): a SCSI command
addressed to a physical disk by its device ID, bypassing the RAID layer. Management tools use it
for INQUIRY, SMART and log pages (`Deny SCSI Passthrough = No`), but the firmware also executes
media READ and WRITE commands sent through it.

`tools/mfi_pt.py` proves it with the stock driver, through the management ioctl
(`MEGASAS_IOC_FIRMWARE` on `/dev/megaraid_sas_ioctl_node`):

```sh
python3 tools/mfi_pt.py 6 4 inquiry
# cmd_status=0x00 scsi_status=0x00
# type=0x00 vendor=b'ATA     ' product=b'WDC WD5003AZEX-0' rev=b'0A80'
python3 tools/mfi_pt.py 6 4 cap
# cmd_status=0x00 scsi_status=0x00 last_lba=0x3a38602f block_size=512
python3 tools/mfi_pt.py 6 4 read 0
```

(`6` = SCSI host number of the controller, `4` = device ID of the disk.)

## The driver side

`megaraid_sas` already contains a complete I/O path for "system PDs", the disks that firmware with
JBOD support exposes to the host. For MFI-series controllers every SCSI command for such a disk is
built as an `MFI_CMD_PD_SCSI_IO` frame. The only thing missing is the list: at init and on events
the driver sends `MR_DCMD_PD_LIST_QUERY` with `MR_PD_QUERY_TYPE_EXPOSED_TO_HOST`, and on the
SAS2108 that list is always empty.

The patch (`driver/expose_ugood_pds.patch`, about 60 lines in `megaraid_sas_base.c`):

1. Adds `module_param(expose_ugood_pds, bool, 0444)`, default off.
2. Splits `megasas_get_pd_list()` into a query helper. After the normal query, if the parameter is
   on and the adapter is `MFI_SERIES`, it runs a second query of type `MR_PD_QUERY_TYPE_STATE`
   with argument `MR_PD_STATE_UNCONFIGURED_GOOD` and adds those disks (SCSI type disk only) to the
   driver's PD list. From there the existing code registers them on the physical channels and
   routes their I/O as pass-through.
3. In the AEN handler, on `LD_CREATED`, `LD_DELETED`, `LD_OFFLINE` and PD state-change (`0x0072`)
   events, it adds `SCAN_PD_CHANNEL`, so the PD list is refreshed and disks appear or disappear
   without reloading the module.

Safety properties that follow from this design:

- Disks that are members of a VD are Online, never UGood, so they are never exposed.
- When a raw disk becomes a VD member, the event removes the raw device before the VD is used.
- Fusion controllers (SAS2208 and newer) are not affected: they have real firmware JBOD and the
  code checks `adapter_type == MFI_SERIES`.
- With the parameter off the code path is the original one.

## Other SAS2108 cards

The same firmware family runs on 9260/9261/9280, Dell PERC H700/H800, IBM ServeRAID M5014/M5015,
Intel RS2xx and others. Nothing in the patch is specific to the 9264-8i, but only the 9264-8i has
been tested.
