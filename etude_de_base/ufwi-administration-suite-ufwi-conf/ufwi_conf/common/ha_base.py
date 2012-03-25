
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

from IPy import IP

from ufwi_rpcd.common import tr

from .ha_statuses import ENOHA, PRIMARY, SECONDARY
from .net_objects_rw import NetRW

PRIMARY_ADDR = '5.0.0.1'
SECONDARY_ADDR = '5.0.0.2'
HA_NET = '5.0.0.0/16'

def hasIPConfiguration(interface, discard_services=False):
    if not discard_services:
        return bool(interface.nets)
    for net in interface.nets:
        if net.primary_ip_addrs | net.secondary_ip_addrs:
            return True
    return False

def any_ha(ha_status):
    return ha_status != ENOHA

def active_ha(ha_status):
    return ha_status in (PRIMARY, SECONDARY)

def haNet():
    """
    High availability hardcoded network config
    """
    label = tr("Network reserved for High Availability")
    primary_ip_addr = set((IP(PRIMARY_ADDR),))
    secondary_ip_addr = set((IP(SECONDARY_ADDR),))
    ip_net = IP(HA_NET)
    return NetRW(label, ip_net, primary_ip_addrs=primary_ip_addr,
            secondary_ip_addrs=secondary_ip_addr)

def getHostnameFormatHA(ha_type):
    """get hostname fmt"""
    if ha_type == SECONDARY:
        return '%s-secondary'
    else:
        return '%s'

