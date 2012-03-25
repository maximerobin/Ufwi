
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

from ufwi_rpcd.common import tr

from .ha_base import haNet
from .ha_statuses import ENOHA
from .ha_statuses import PENDING_PRIMARY
from .ha_statuses import PENDING_SECONDARY
from .ha_statuses import PRIMARY
from .ha_statuses import SECONDARY

def getHaIp(network, ha_status):
    #
    #A note on the definition of the "ips" variable
    #
    # Type: tuple
    #
    # The content of the "ips" set depends on the status of the appliance
    # regarding high availability (HA).
    # Not in high availability ?
    # Then we affect the service ips in /etc/network interfaces.
    # In high availability, these ips are affected BY HEARTBEAT.
    #
    # It is mandatory, in order to configure the corresponding interfaces, that
    # the interface that has service IP(s) on a given net IP ALSO has primary AND secondary IPs on this net.
    #
    # Therefore, affectation as follows:
    # [ENOHA] - not in HA
    # - use service IPs
    # [PRIMARY]
    # - use primary IPs
    # [SECONDARY]
    # - use secondary IPs
    # [PENDING_PRIMARY] - waiting for heartbeat to be configured, we take over the service IPs
    # AND primary because the latter are used to establish the communication with the secondary node.
    # - use primary and service IPs

    # if an entry have 'service_ip_addrs' and ('primary_ip_addrs' or
    # 'secondary_ip_addrs') specified, 'service_ip_addrs' MUST be last
    # in order to be 'secondary ip' (cf command "ip"), else others ip will
    # be removed by heartbeat during heartbeat shutdown.
    ip_addrs_to_up = {
        ENOHA:              tuple(network.service_ip_addrs),
        PENDING_PRIMARY:    tuple(network.primary_ip_addrs) + tuple(network.service_ip_addrs),
        PRIMARY:            tuple(network.primary_ip_addrs),
        PENDING_SECONDARY:  tuple(network.secondary_ip_addrs) + tuple(network.service_ip_addrs),
        SECONDARY:          tuple(network.secondary_ip_addrs),
    }
    return ip_addrs_to_up[ha_status]

def ha_interface_check(interface):
    if interface.hasHA():
        if len(interface.nets) != 1:
            return False, tr(
                "There must be exactly one network "
                "defined for the %s HA interface"
                ) % interface.fullName()
        if len(interface.routes) != 0:
            return False, tr(
                "There must be no defined route "
                "for the %s HA interface"
                ) % interface.fullName()

        supposed_ha_net = iter(interface.nets).next()
        if not supposed_ha_net.equalsSystemWise(haNet()):
            return False, tr(
                "The network configured on %s "
                "is not the expected HA network"
                ) % interface.fullName()
    return True, "ok"
