# 7. What did not work (and what can hurt the card)

Everything below was tried on the same 9264-8i before the driver approach. Read it before trying
any of it yourself.

| Attempt | Result |
|---|---|
| `storcli64 /c0 set jbod=on` | `Controller does not support JBOD` |
| `MegaCli64 -AdpSetProp EnableJBOD 1 -a0` (8.07.14) | `Failed to Set Adapter Properties`; nothing changed |
| IT firmware (`2118it.bin`, `sas2flash`) | There is no IT firmware for the SAS2108. IT crossflash exists only from SAS2208 (9265/9266/9271, H710) and for SAS2008 cards. `sas2flash` does not see a 2108 |
| LSI firmware 12.15.0-0239 | `Support JBOD = No` |
| IBM ServeRAID M5000 firmware 12.15.0-0248 ("JBOD mode" in its change log) | Flashes fine on the 9264-8i, but `Support JBOD = No`; `set jbod=on` and `EnableJBOD 1` still refused. JBOD is gated by the card identity/NVDATA, not by the firmware build |
| MegaOEM MFC dump | `enableJBOD = 0`; not changed |
| Changing the SBR (PCI subsystem → IBM M5014 `1014:03c7`) with `lsirec` | Written and verified, but **the firmware restored the original SBR on the next boot** (a factory copy is kept outside the firmware image). Making it stick needs `megarec -cleanflash` |
| `megarec -cleanflash` + M5014 SBR + `m0flash` from FreeDOS **inside a VM** (PCI passthrough) | Card came up as `1014:03c7`, but flashing failed (`Error code = 64`), and a second `cleanflash` with an image **crashed the host**. The card was left with an empty flash; it was later brought back to `1000:0079`/`1000:9264` with the IBM 12.15.0-0248 image on bare metal. Do not run `megarec` in a VM |

## Hazards

- **`lsirec` on a MegaRAID card**: every command "unlocks" the chip by writing the MPT doorbell
  register (BAR1+0x04). On a 2108 this causes completer aborts and AER bursts. With `megaraid_sas`
  bound, the firmware goes to `FAULT` (`Fault code 0x10000`) and shutdown can hang (needed the power
  button once). If you must use it: `lsirec unbind` first, keep the driver unloaded, and read the
  SBR at least twice and compare.
- **`megarec -readsbr` in a VM** returned corrupted bits (I²C timing); trust only repeated
  identical reads.
- PCIe passthrough of this card on X58 needs `allow_unsafe_interrupts` and `rombar=0`; errors from
  the card escalate to `vfio ... Unrecoverable` and stop the VM.

## Why the driver approach instead

The firmware already accepts SCSI pass-through to physical disks for media I/O. Using that from
the driver needs no flashing, no change to the card's identity, can be turned off with one module
parameter, and the stock firmware's RAID functions keep working next to it.
