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

INTERFACE_RESTYPE = u'INTERFACE'
FIREWALL_RESTYPE = u'FIREWALL'
NETWORK_RESTYPE = u'NETWORK'
IPSEC_NETWORK_RESTYPE = u'IPSEC_NETWORK'
HOST_RESTYPE = u'HOST'
GENERIC_INTERFACE_RESTYPE = u'GENERIC_INTERFACE'
GENERIC_NETWORK_RESTYPE = u'GENERIC_NETWORK'
GENERIC_HOST_RESTYPE = u'GENERIC_HOST'
HOSTNAME_RESTYPE = u'HOSTNAME'
GROUP_RESTYPE = u'NETWORK_GROUP'

RESOURCE_TYPES = (
    INTERFACE_RESTYPE, FIREWALL_RESTYPE, NETWORK_RESTYPE,
    HOST_RESTYPE, GENERIC_INTERFACE_RESTYPE, GENERIC_NETWORK_RESTYPE,
    GENERIC_HOST_RESTYPE, HOSTNAME_RESTYPE)

INTERNET_IPV4 = IP('0.0.0.0/0')
INTERNET_IPV6 = IP('2000::/3')

IPV4_ADDRESS = u"IPv4"
IPV6_ADDRESS = u"IPv6"
INTERFACE_ADDRESS = u"interface"

IPTABLES_TABLES = {
    IPV4_ADDRESS : ("filter", "nat", "mangle"),
    IPV6_ADDRESS : ("filter", "mangle"),
}

# Interface name regex: "br0", "eth1.2", "eth0:3", "vpn.support", ...
INTERFACE_NAME_REGEX_STR = u'^[^\x00-\x20]{1,14}$'

def isNetwork(ip):
    size = ip.prefixlen()
    if ip.version() == 6:
        return size < 128
    else:
        return size < 32

