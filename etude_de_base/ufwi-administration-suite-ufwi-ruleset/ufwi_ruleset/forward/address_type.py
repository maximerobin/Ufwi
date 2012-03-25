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

from ufwi_rpcd.backend import tr
from ufwi_ruleset.common.network import INTERFACE_ADDRESS

def checkAddressTypes(src_types, dst_types):
    """
    >>> from ufwi_ruleset.common.network import IPV4_ADDRESS, IPV6_ADDRESS
    >>> empty = set()
    >>> ipv4 = set((IPV4_ADDRESS,))
    >>> ipv6 = set((IPV6_ADDRESS,))
    >>> interface = set((INTERFACE_ADDRESS,))
    >>> ipv46 = ipv4 | ipv6
    >>> interface4 = interface | ipv4
    >>> interface6 = interface | ipv6
    >>> interface46 = interface | ipv4 | ipv6

    Valid IP addresses combinaisons:

    >>> checkAddressTypes(ipv4, ipv4)
    True
    >>> checkAddressTypes(ipv6, ipv6)
    True

    Invalid IP addresses combinaison:

    >>> checkAddressTypes(empty, ipv6)
    False
    >>> checkAddressTypes(ipv4, ipv6)
    False

    Two address types as source:

    >>> checkAddressTypes(ipv46, ipv4)
    False
    >>> checkAddressTypes(ipv46, ipv6)
    False
    >>> checkAddressTypes(ipv46, ipv46)
    False
    >>> checkAddressTypes(ipv46, interface4)
    False
    >>> checkAddressTypes(ipv46, interface6)
    False
    >>> checkAddressTypes(ipv46, interface46)
    False

    Valid interfaces combinaisons:

    >>> checkAddressTypes(interface4, ipv4)
    True
    >>> checkAddressTypes(interface6, ipv6)
    True
    >>> checkAddressTypes(interface46, ipv6)
    True
    >>> checkAddressTypes(interface46, interface46)
    True

    Invalid interfaces combinaisons:

    >>> checkAddressTypes(interface4, empty)
    False
    >>> checkAddressTypes(interface4, ipv6)
    False
    >>> checkAddressTypes(interface6, ipv4)
    False
    >>> checkAddressTypes(interface4, interface6)
    False
    """
    if (not src_types) or (not dst_types):
        return False
    if (INTERFACE_ADDRESS in src_types) \
    and (INTERFACE_ADDRESS in dst_types) \
    and src_types == dst_types:
            return True
    interface_set = set((INTERFACE_ADDRESS,))
    if INTERFACE_ADDRESS in src_types:
        src_types = set(src_types) - interface_set
    else:
        if len(src_types) != 1:
            return False
    if INTERFACE_ADDRESS in dst_types:
        dst_types -= interface_set
    else:
        if len(dst_types) != 1:
            return False
    return (src_types <= dst_types) or (dst_types <= src_types)

def formatAddressTypes(families):
    if families:
        return u', '.join(families)
    else:
        return tr('(none)')

