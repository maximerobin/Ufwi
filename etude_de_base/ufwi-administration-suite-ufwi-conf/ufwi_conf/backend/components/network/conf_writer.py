#coding: utf-8
"""
$Id$


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


from os import chmod
from IPy import IP

from ufwi_rpcd.common import EDENWALL
from ufwi_rpcd.common.error import exceptionAsUnicode
from ufwi_rpcd.backend import Component
from ufwi_conf.common.net_exceptions import NetCfgError
from ufwi_conf.common.net_interfaces import Bonding
from ufwi_conf.common.net_interfaces import Vlan
from ufwi_conf.common.net_base import hasIPConfiguration, any_ha, active_ha
if EDENWALL:
    from ufwi_conf.common.net_ha import getHaIp
    from ufwi_conf.common.ha_cfg import getHAInterface

PREAMBLE = """\
## /etc/network/interfaces
# This file was written automatically by edenwall, please do not change it.
# Your changes will be lost!
#
"""

LO_DEFINITION = """

auto lo
iface lo inet loopback

"""

ETHERNET_BANNER = """
######### Ethernets Interfaces ###########
"""

BONDING_BANNER = """
######### Bonding Interfaces ###########
"""

VLAN_BANNER = """
######### Vlan Interfaces ###########
"""


def writeNets(fd, ha_status, interface, ordered_nets):
    for phase in ('pre-up pre-down'.split()):
        fd.write('    %s ip addr flush dev %s ||:\n' % (phase, interface.system_name))

    for net_index, net in enumerate(ordered_nets):
        if EDENWALL:
            ips = getHaIp(net, ha_status)
        else:
            ips = net.ip_addrs

        for ip_index, ip in enumerate(ips):

            if net.net.version() == 6:
                netmask = net.net.prefixlen()
            else:
                netmask = net.net.netmask()
            broadcast = net.net.broadcast()
            address = unicode(ip)

            if net_index + ip_index == 0:
                fd.write('    address %s\n' % address)
                fd.write('    netmask %s\n' % netmask)
                fd.write('    broadcast %s\n' % broadcast)
            else:
                prefix_len = net.net.prefixlen()
                fd.write('    post-up ip addr add dev %s %s/%s broadcast %s ||:\n' %
                (interface.system_name, address, prefix_len, broadcast))

def writeRoutes(fd, interface):
    fd.write('    pre-down ip route flush dev %s ||:\n' % interface.system_name)
    for route in interface.routes:
        arg = 'ip'
        if route.dst.version() == 6:
            arg += ' -6'
        arg += ' route add'
        if route.dst == IP('::/0'):
            arg += ' default'
        else:
            arg += ' %s' % route.dst
        arg += ' via %s dev %s' % (route.router, interface.system_name)
        fd.write('    post-up %s ||:\n' % arg)

def writeEthernet(f, netcfg, ha_status, ethernet):
    ordered_nets = tuple(ethernet.nets)
    autonomous = hasIPConfiguration(ethernet)

    writePreamble(f, netcfg, ethernet, ordered_nets, autonomous=autonomous)
    if autonomous:
        writeNets(f, ha_status, ethernet, ordered_nets)
        writeRoutes(f, ethernet)
    f.write('\n')

def addStatement(fd, phase_and_cmd, ignore_fail=True):
    if ignore_fail:
        ending =  '||:\n'
    else:
        ending =  '\n'
    fd.write('    %s %s' % (phase_and_cmd, ending))

def writeBonding(f, netcfg, ha_status, bonding, is_first=False):
    ordered_nets = tuple(bonding.nets)
    discard_services = any_ha(ha_status)
    autonomous = hasIPConfiguration(bonding, discard_services=discard_services)
    #autonomous=True:
    #always mark bonding auto
    writePreamble(f, netcfg, bonding, ordered_nets, autonomous=True)
    if is_first:
        addStatement(f, 'pre-up modprobe bonding')

    for statement in (
        'pre-up echo +%s > /sys/class/net/bonding_masters' % bonding.system_name,
        'pre-down echo -%s > /sys/class/net/bonding_masters' % bonding.system_name
    ):
        addStatement(f, statement)

    sorted_ethernets = list(bonding.ethernets)
    sorted_ethernets.sort()
    for ethernet in sorted_ethernets:
        for statement in (
            'up /sbin/ifenslave %s %s' % (bonding.system_name, ethernet.system_name),
            'down /sbin/ifenslave %s -d %s' % (bonding.system_name, ethernet.system_name)
        ):
            addStatement(f, statement)

    if autonomous:
        writeNets(f, ha_status, bonding, ordered_nets)
        writeRoutes(f, bonding)
    else:
        forceCreation(f, bonding)

    f.write('\n')

def writeVlan(f, netcfg, ha_status, vlan):
    ordered_nets = tuple(vlan.nets)

    discard_services = any_ha(ha_status)
    autonomous = hasIPConfiguration(vlan, discard_services=discard_services)

    # Always add preamble and vlan-raw-device
    writePreamble(f, netcfg, vlan, ordered_nets)
    if autonomous:
        writeNets(f, ha_status, vlan, ordered_nets)
        writeRoutes(f, vlan)
    else:
        forceCreation(f, vlan)
    addStatement(
        f,
        'vlan-raw-device %s' % vlan.raw_device,
        ignore_fail=True
        )
    f.write('\n')

def forceCreation(output, iface):
    """
    dirty fix:
    a bonding won't go up on our grsec kernel if it has no IP address
    We're allocating one, then delete it, and voilà.
    from the "14/8" address space
    """
    ip = IP("14.0.0.0").int() + iface.id
    ip = str(IP(ip)) + "/8"
    for statement in (
        "#this address helps ifuping the bonding on a reserved IP range",
        "address %s" % ip,
        "netmask 255.0.0.0",
        "broadcast 14.255.255.255",
        "#As soon as the interface is up, we remove this unnecessary address",
        "post-up ip addr del %s dev %s" % (ip, iface.system_name)
        ):
        addStatement(output, statement)

def iterSpecifiedInterfaces(netcfg, down=False):
    """
    When 'down' is True, gives interfaces in p2p, vlan, bonding, eth order

    When 'down' is False, gives them in the reverse order (building order)
    """
    for interface in netcfg.iterInterfaces(reverse=down):
        if isInterfaceSpecified(interface):
            yield interface

def isInterfaceSpecified(interface, ha_status=None):
    discard_services = active_ha(ha_status)
    return (
        isinstance(interface, Bonding)
        or
        isinstance(interface, Vlan)
        or
        hasIPConfiguration(interface, discard_services=discard_services)
        )

def writePreamble(fd, netcfg, interface, ordered_nets, autonomous=True):
    if autonomous:
        method = 'static'
    else:
        method = 'manual'

    #auto up: normally all interfaces, but only lo and HA interfaces in a failover setup
    if EDENWALL:
        ha_iface = getHAInterface(netcfg)
    else:
        ha_iface = None

    #there are problems in HA when a bonding has vlans built on it that only have services IPs
    bonding_with_vlans = isinstance(interface, Bonding) and interface.vlans

    if interface is ha_iface or hasIPConfiguration(interface) or (bonding_with_vlans):
        fd.write('auto %s\n' % interface.system_name)

    #Prefix
    if len(ordered_nets) == 0 or ordered_nets[0].net.version() == 4:
        inet_string = 'inet'
    else:
        inet_string = 'inet6'
    fd.write('iface %s %s %s\n' % (interface.system_name, inet_string, method))

def writeConf(netcfg, interfaces_file, ha_status):
    if isinstance(interfaces_file, file):
        f = interfaces_file
        close_f = False
    else:
        close_f = True
        try:
            f = open(interfaces_file, 'w')
        except IOError, err:
            raise NetCfgError(
                'Unable to write the configuration to "%s"! %s',
                interfaces_file, exceptionAsUnicode(err))
    f.write(PREAMBLE)
    f.write("#File generated by EdenWall: %s\n" % Component.timestamp())

    # write lo, no logic involved
    f.write(LO_DEFINITION)

    if netcfg.ethernets:
        f.write(ETHERNET_BANNER)
        ethernets = list(netcfg.iterEthernets())
        ethernets.sort()
        for ethernet in ethernets:
            if isInterfaceSpecified(ethernet, ha_status=ha_status):
                writeEthernet(f, netcfg, ha_status, ethernet)

    if netcfg.bondings:
        f.write(BONDING_BANNER)
        bondings = list(netcfg.iterBondings())
        bondings.sort()

        first_bonding = True

        for bonding in bondings:
            writeBonding(f, netcfg, ha_status, bonding, is_first=first_bonding)
            first_bonding = False

    if netcfg.vlans:
        f.write(VLAN_BANNER)
        vlans = list(netcfg.iterVlans())
        vlans.sort()

        for vlan in vlans:
            writeVlan(f, netcfg, ha_status, vlan)

    if close_f:
        f.close()
        chmod(interfaces_file, 0644)
    return True

