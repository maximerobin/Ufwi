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

from ufwi_ruleset.forward.resource import Resource
from ufwi_ruleset.common.network import (FIREWALL_RESTYPE,
    IPV4_ADDRESS, IPV6_ADDRESS, INTERFACE_ADDRESS)

class FirewallResource(Resource):
    TYPE = FIREWALL_RESTYPE

    def __init__(self, resources, netcfg, loader_context=None):
        attr = {
            'id': u'Firewall',
            'editable': False,
        }
        Resource.__init__(self, resources, resources, self, attr, loader_context)
        self.allow_child = False
        self.address_types = set((INTERFACE_ADDRESS, IPV4_ADDRESS, IPV6_ADDRESS))
        self.addresses = list(netcfg.iterAddresses())

    def __unicode__(self):
        return tr('The firewall')

    def getAddressTypes(self):
        return self.address_types

    def hasAddresses(self):
        return True

    def getAddresses(self):
        return self.addresses

    def exportXML(self, parent):
        return None

    def match(self, other):
        return (other.type == FIREWALL_RESTYPE)

