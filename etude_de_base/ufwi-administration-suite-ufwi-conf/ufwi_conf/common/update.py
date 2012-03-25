import re
from ufwi_rpcd.common import EDENWALL

UPGRADE_STATUS_ALREADY_APPLIED = 'Already applied'
UPGRADE_STATUS_FAILED = 'FAILED'
UPGRADE_STATUS_IN_PROGRESS = 'In progress'
UPGRADE_STATUS_NEED_RESTART = 'Need restart'
UPGRADE_STATUS_NEW = 'New'
UPGRADE_STATUS_DEPENDENCIES_MISSING = 'Dependencies missing'
UPGRADE_RESTART_NEED_NAMES = {
    'system': 'the system',
    'ufwi_rpcd': 'the configuration service',
}

if EDENWALL:
    UPGRADE_PREFIX = 'edenwall4_upgrade_'
else:
    UPGRADE_PREFIX = 'nufirewall_upgrade_'
UPGRADE_NUMBER_RE = re.compile('^' + UPGRADE_PREFIX + r'(\d+)\.tar$')
UPGRADE_RE = re.compile(r'%s(\d+).tar$'% UPGRADE_PREFIX)

def upgrade_number(filename):
    match = UPGRADE_NUMBER_RE.search(filename)
    if match:
        return int(match.group(1))
    else:
        return None

