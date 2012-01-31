# FIXME: Write better regex

# "192.168.0.1"
IPV4_REGEX_STR = ur'[12]?[0-9]?[0-9]\.[12]?[0-9]?[0-9]\.[12]?[0-9]?[0-9]\.[12]?[0-9]?[0-9]'

# "ff02::", "::ffff:192.168.0.1"
IPV6_REGEX_STR = ur'[0-9A-Fa-f]*:[:0-9A-Fa-f]+'
NET_IPV6_STR = '[0-9A-Fa-f]*:[:0-9A-Fa-f]+/1?[0-9][0-9]'

# have to be compiled in case insensitive
HOSTNAME_REGEX_STR_PART = ur'[a-zA-Z0-9-][0-9a-zA-Z_-]+'
FQDN_REGEX_STR_PART = ur'[a-z0-9][a-z0-9_-]*(?:\.[a-z0-9][a-z0-9_-]*)+'
HOSTNAME_OR_FQDN_REGEX_PART =  ur'(?:%s|%s)' % (HOSTNAME_REGEX_STR_PART, FQDN_REGEX_STR_PART)

HOSTNAME_REGEX_STR = ur'^%s$' % HOSTNAME_REGEX_STR_PART
FQDN_REGEX_STR = u'^%s$' % FQDN_REGEX_STR_PART
HOSTNAME_OR_FQDN_REGEX_STR =  ur'^%s$' % HOSTNAME_OR_FQDN_REGEX_PART
MAIL_REGEX_STR = u'^[a-zA-Z0-9_%.+-]+@' + HOSTNAME_OR_FQDN_REGEX_PART  + u'$'

NET_ALL_REGEX_STR = u'^(%s/((%s)|([123]?[0-9])))|(%s)$' % (IPV4_REGEX_STR, IPV4_REGEX_STR, NET_IPV6_STR)

# TODO: make this regexp check for complete DN (currently matches CN=blah only, should match CN=blah,OU=blah2)
DN_REGEXP_STR = '[A-Za-z0-9.-]+=[^=]+'

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


def isHost(address):
    """
    >>> from IPy import IP
    >>> isHost(IP('192.168.0.1'))
    True
    >>> isHost(IP('192.168.0.0/24'))
    False
    """
    size = address.prefixlen()
    if address.version() == 6:
        return (size == 128)
    else:
        return (size == 32)

def isIpInNetwork(ip, network):
    """
    >>> from IPy import IP
    >>> ip_1 = IP('192.168.0.1')
    >>> net_1 = IP('192.168.0.0/24')
    >>> net_2 = IP('192.168.1.0/24')
    >>> isIpInNetwork(ip_1, net_1)
    True
    >>> isIpInNetwork(ip_1, net_2)
    False
    >>> isIpInNetwork(ip_1, ip_1)
    False
    >>> isIpInNetwork(net_1, net_2)
    False
    >>> ip6 = IP('FF::1')
    >>> net6 = IP('FF::0/32')
    >>> isIpInNetwork(ip6, net6)
    True
    >>> isIpInNetwork(ip_1, net6)
    False
    >>> isIpInNetwork(ip6, net_1)
    False
    """
    if not isHost(ip):
        return False

    if isHost(network):
        return False

    if ip.version() != network.version():
        return False

    return ip in network
