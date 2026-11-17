#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Add the expose_ugood_pds module parameter to megaraid_sas_base.c.

On MFI-series controllers (SAS2108 and friends) the firmware never reports any
disk as a "system PD" (firmware JBOD), so the driver exposes nothing but virtual
drives. With expose_ugood_pds=1 the driver also asks the firmware for the PDs
in the Unconfigured Good state and registers them with the SCSI mid-layer.
Their I/O goes through the path the driver already has for system PDs:
MFI_CMD_PD_SCSI_IO (SCSI pass-through to a physical disk).

The PD list is also re-read on VD create/delete/offline and PD state-change
events, so a disk disappears as soon as it becomes a VD member and comes back
when it is Unconfigured Good again.

Usage: patch_expose_ugood.py path/to/drivers/scsi/megaraid/megaraid_sas_base.c

Applies unchanged to upstream Linux v5.4 .. v7.0 (checked textually); the
script aborts without writing anything if a hunk does not match exactly once.
"""
import sys

path = sys.argv[1]
src = open(path).read()

if 'expose_ugood_pds' in src:
    sys.exit('already patched')


def rep(old, new, count=1):
    global src
    n = src.count(old)
    if n != count:
        sys.exit(f'hunk found {n}x (expected {count}):\n{old}')
    src = src.replace(old, new)


rep('module_param(scmd_timeout, int, 0444);\n',
    'module_param(scmd_timeout, int, 0444);\n'
    'static bool expose_ugood_pds;\n'
    'module_param(expose_ugood_pds, bool, 0444);\n'
    'MODULE_PARM_DESC(expose_ugood_pds, "Expose Unconfigured Good PDs to the OS as '
    'pass-through disks (pseudo-JBOD, MFI series only). Default: 0");\n')

rep('static int\nmegasas_get_pd_list(struct megasas_instance *instance)\n{\n',
    'static int\nmegasas_get_pd_list_pass(struct megasas_instance *instance, u8 qtype,\n'
    '\t\t\t u8 qarg, bool first)\n{\n')

rep('\tif (instance->pd_list_not_supported) {\n'
    '\t\tdev_info(&instance->pdev->dev, "MR_DCMD_PD_LIST_QUERY "\n'
    '\t\t"not supported by firmware\\n");\n'
    '\t\treturn ret;\n'
    '\t}\n\n'
    '\tci = instance->pd_list_buf;\n',
    '\tci = instance->pd_list_buf;\n')

rep('\tdcmd->mbox.b[0] = MR_PD_QUERY_TYPE_EXPOSED_TO_HOST;\n\tdcmd->mbox.b[1] = 0;\n',
    '\tdcmd->mbox.b[0] = qtype;\n\tdcmd->mbox.b[1] = qarg;\n')

rep('\tswitch (ret) {\n\tcase DCMD_FAILED:\n\t\tdev_info(&instance->pdev->dev, "MR_DCMD_PD_LIST_QUERY "\n',
    '\tswitch (ret) {\n\tcase DCMD_FAILED:\n'
    '\t\tif (!first) {\n'
    '\t\t\tdev_warn(&instance->pdev->dev,\n'
    '\t\t\t\t "expose_ugood_pds: PD query type %u/%u failed\\n",\n'
    '\t\t\t\t qtype, qarg);\n'
    '\t\t\tbreak;\n'
    '\t\t}\n'
    '\t\tdev_info(&instance->pdev->dev, "MR_DCMD_PD_LIST_QUERY "\n')

rep('\t\tmemset(instance->local_pd_list, 0,\n\t\t\t\tMEGASAS_MAX_PD * sizeof(struct megasas_pd_list));\n\n'
    '\t\tfor (pd_index = 0; pd_index < le32_to_cpu(ci->count); pd_index++) {\n',
    '\t\tif (first)\n'
    '\t\t\tmemset(instance->local_pd_list, 0,\n\t\t\t\tMEGASAS_MAX_PD * sizeof(struct megasas_pd_list));\n\n'
    '\t\tfor (pd_index = 0; pd_index < le32_to_cpu(ci->count); pd_index++) {\n'
    '\t\t\tif (!first) {\n'
    '\t\t\t\tif (pd_addr->scsiDevType != TYPE_DISK) {\n'
    '\t\t\t\t\tpd_addr++;\n'
    '\t\t\t\t\tcontinue;\n'
    '\t\t\t\t}\n'
    '\t\t\t\tdev_info(&instance->pdev->dev,\n'
    '\t\t\t\t\t "expose_ugood_pds: PD %u (UGood) exposed as pass-through disk\\n",\n'
    '\t\t\t\t\t le16_to_cpu(pd_addr->deviceId));\n'
    '\t\t\t}\n')

# VD create/delete/offline and PD state changes alter which disks are UGood:
# rescan the PD channel so raw disks appear/disappear without reloading the driver.
rep('\t\tdefault:\n\t\t\tevent_type = 0;\n\t\t\tbreak;\n\t\t}\n\t} else {\n',
    '\t\tdefault:\n\t\t\tevent_type = 0;\n\t\t\tbreak;\n\t\t}\n'
    '\t\tif (expose_ugood_pds && instance->adapter_type == MFI_SERIES) {\n'
    '\t\t\tswitch (le32_to_cpu(instance->evt_detail->code)) {\n'
    '\t\t\tcase MR_EVT_LD_CREATED:\n'
    '\t\t\tcase MR_EVT_LD_DELETED:\n'
    '\t\t\tcase MR_EVT_LD_OFFLINE:\n'
    '\t\t\tcase 0x0072: /* MR_EVT_PD_STATE_CHANGE */\n'
    '\t\t\t\tevent_type |= SCAN_PD_CHANNEL;\n'
    '\t\t\t\tbreak;\n'
    '\t\t\t}\n'
    '\t\t}\n'
    '\t} else {\n')

# wrapper placed right after the renamed function
start = src.index('megasas_get_pd_list_pass(struct megasas_instance *instance, u8 qtype,')
end = src.index('\n\treturn ret;\n}\n', start) + len('\n\treturn ret;\n}\n')
wrapper = '''
static int
megasas_get_pd_list(struct megasas_instance *instance)
{
	int ret;

	if (instance->pd_list_not_supported) {
		dev_info(&instance->pdev->dev, "MR_DCMD_PD_LIST_QUERY "
		"not supported by firmware\\n");
		return 0;
	}

	ret = megasas_get_pd_list_pass(instance, MR_PD_QUERY_TYPE_EXPOSED_TO_HOST,
				       0, true);
	if (ret == DCMD_SUCCESS && expose_ugood_pds &&
	    instance->adapter_type == MFI_SERIES)
		megasas_get_pd_list_pass(instance, MR_PD_QUERY_TYPE_STATE,
					 MR_PD_STATE_UNCONFIGURED_GOOD, false);
	return ret;
}
'''
src = src[:end] + wrapper + src[end:]
open(path, 'w').write(src)
print('patch applied')
