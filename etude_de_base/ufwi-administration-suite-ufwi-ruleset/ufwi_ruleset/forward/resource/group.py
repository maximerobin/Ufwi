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
from ufwi_rpcd.common.tools import getFirst

from ufwi_ruleset.common.network import GROUP_RESTYPE

from ufwi_ruleset.forward.error import RulesetError
from ufwi_ruleset.forward.group import Group, ObjectList
from ufwi_ruleset.forward.resource.tools import checkNetworkInclusion
from ufwi_ruleset.forward.resource import (ResourcesContainer,
    NetworkResource, HostResource, HostnameResource)

class NetworkList(ObjectList):
    def getter(self, group, name, identifier):
        resources = group.library.resources
        return resources[identifier]

class NetworkGroup(Group, ResourcesContainer):
    objects = NetworkList()

    def __init__(self, resources, values, loader_context=None):
        Group.__init__(self, resources, values, loader_context)
        ResourcesContainer.__init__(self, resources)
        self.interface = getFirst(self.objects).interface
        self.parent = self.interface
        self.allow_child = False
        self.type = GROUP_RESTYPE

    def checkConsistency(self, loader_context=None):
        checkNetworkInclusion(self, self.objects)
        for object in self.objects:
            if isinstance(object, (NetworkResource, HostResource, HostnameResource)):
                continue
            raise RulesetError(tr('A network group can only contain networks, hosts or hostnames (not "%s").'), object.type)

    def iterChildren(self, recursive=False):
        return iter(tuple())

