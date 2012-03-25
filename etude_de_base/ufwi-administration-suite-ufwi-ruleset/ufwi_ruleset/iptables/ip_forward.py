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

from ufwi_rpcd.common.transaction import Transaction
from ufwi_rpcd.backend.logger import Logger
from ufwi_ruleset.iptables.sysctl import sysctlGet, sysctlSet

class IPForward(Transaction, Logger):
    def __init__(self, enable, ipv6, logger):
        if ipv6:
            name = 'ipv6_forward'
        else:
            name = 'ipv4_forward'
        Logger.__init__(self, name, parent=logger)
        self.enable = enable
        if ipv6:
            self.sysctl_key = u'net.ipv6.conf.all.forwarding'
        else:
            self.sysctl_key = u'net.ipv4.ip_forward'

    def save(self):
        value = sysctlGet(self.sysctl_key)
        self.was_enabled = (value == '1')
        self.info("Get current state: %s" % self.was_enabled)

    def setState(self, enabled):
        if enabled:
            self.warning("Enable forward")
            value = u'1'
        else:
            self.warning("Disable forward")
            value = u'0'
        sysctlSet(self, self.sysctl_key, value)

    def apply(self):
        self.setState(self.enable)

    def restore(self):
        self.setState(self.was_enabled)

