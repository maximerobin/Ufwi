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

from ufwi_rpcd.common.tools import getFirst

from ufwi_ruleset.forward.group import Group
from ufwi_ruleset.forward.platform import Platform
from ufwi_ruleset.forward.tools import zipall

def getFirstObject(objects):
    return getFirst(flattenObjectList(objects))

def getFirstNetwork(objects):
    return getFirst(flattenNetworkList(objects))

def getFirstProtocol(objects):
    return getFirst(flattenProtocolList(objects))

def zipallObjects(*object_lists):
    iterables = tuple(flattenObjectList(object_list)
        for object_list in object_lists)
    return zipall(*iterables)

def flattenObject(obj, include_protocol=True, include_network=True):
    if isinstance(obj, Group):
        group = obj
        for obj in group.objects:
            yield obj
    elif isinstance(obj, Platform):
        platform = obj
        for item in platform.items:
            # item.network/protocol can be single object or a group
            if include_network:
                for obj in flattenNetwork(item.network):
                    yield obj
            if include_protocol:
                for obj in flattenProtocol(item.protocol):
                    yield obj
    else:
        yield obj

def flattenObjectList(objects, include_protocol=True, include_network=True):
    for obj in objects:
        for item in flattenObject(obj, include_protocol, include_network):
            yield item

def flattenNetwork(obj):
    for network in flattenObject(obj, include_protocol=False, include_network=True):
        yield network

def flattenProtocol(obj):
    for protocol in flattenObject(obj, include_protocol=True, include_network=False):
        yield protocol

def flattenNetworkList(objects):
    for obj in flattenObjectList(objects, include_protocol=False, include_network=True):
        yield obj

def flattenProtocolList(objects):
    for obj in flattenObjectList(objects, include_protocol=True, include_network=False):
        yield obj

