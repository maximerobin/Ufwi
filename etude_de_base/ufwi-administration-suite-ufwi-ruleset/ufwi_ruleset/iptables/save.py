"""
Copyright (C) 2009-2011 EdenWall Technologies

This file is part of NuFirewall. 
 
 NuFirewall is free software: you can redistribute it and/or modify 
 it under the terms of the GNU General Public License as published by 
 the Free Software Foundation, version 3 of the License. 
 
 NuFirewall is distributed in the hope that it will be useful, 
 but WITHOUT ANY WARRANTY; without even the implied warranty of 
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the 
 GNU General Public License for more details. 
 
 You should have received a copy of the GNU General Public License 
 along with NuFirewall.  If not, see <http://www.gnu.org/licenses/>
"""

from __future__ import with_statement
from os.path import join as path_join, getsize, exists

from ufwi_rpcd.backend import tr
from ufwi_rpcd.backend.process import runCommandAsRoot

from ufwi_ruleset.config import RULESET_DIR
from ufwi_ruleset.iptables.config import IPTABLES_SAVE, IP6TABLES_SAVE, MODPROBE
from ufwi_ruleset.iptables import IptablesError

def loadKernelModules(logger, ipv6):
    """
    Load kernel modules required to use iptables-save and ip6tables-save.
    Do not raise an error if the module loading fails.
    """
    if ipv6:
        proc_filename = '/proc/net/ip6_tables_names'
        module_name = 'ip6table_filter'
    else:
        proc_filename = '/proc/net/ip_tables_names'
        module_name = 'iptable_filter'
    if not exists(proc_filename):
        # Ignore exit code
        runCommandAsRoot(logger, [MODPROBE, module_name], 15.0)
    else:
        logger.info("Don't load kernel module %s: %s is present"
            % (module_name, proc_filename))

def iptablesSave(logger, ipv6):
    """
    Save current iptables rules into a file.
    Return the filename of the saved rules.
    Raise an IptablesError on error.
    """
    if ipv6:
        filename = 'old_rules_ipv6'
        address_type = "IPv6"
    else:
        filename = 'old_rules_ipv4'
        address_type = "IPv4"
    filename = path_join(RULESET_DIR, filename)
    logger.warning("Save %s iptables rules to %s" % (address_type, filename))
    if ipv6:
        command_str = IP6TABLES_SAVE
    else:
        command_str = IPTABLES_SAVE
    command = (command_str,)
    with open(filename, 'w') as rules:
        process, code = runCommandAsRoot(logger, command, timeout=22.5, stdout=rules)
    if code != 0:
        raise IptablesError(tr("%s command exited with code %s!"), command_str, code)
    size = getsize(filename)
    if not size:
        raise IptablesError(tr("%s command output is empty!"), command_str)
    return filename

