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

import re
from ufwi_rpcd.backend import tr

from ufwi_ruleset.common.network import (
    INTERFACE_RESTYPE, GENERIC_INTERFACE_RESTYPE,
    INTERFACE_ADDRESS, IPV4_ADDRESS, IPV6_ADDRESS)
from ufwi_ruleset.common.network import INTERFACE_NAME_REGEX_STR

from ufwi_ruleset.forward.error import RulesetError
from ufwi_ruleset.forward.attribute import Unicode
from ufwi_ruleset.forward.resource import (Resource, NetworkGroup,
    NetworkResource, HostResource, HostnameResource)

def checkName(id):
    if not isinstance(id, unicode):
        raise RulesetError(tr("Invalid identifier: type is not unicode (%s)"), unicode(type(id)))
    if not id:
        raise RulesetError(tr("Invalid identifier: empty string"))

NAME_REGEX = re.compile(INTERFACE_NAME_REGEX_STR)

class Name(Unicode):
    def getter(self, object, name, value):
        name = Unicode.getter(self, object, name, value)
        if not NAME_REGEX.match(name):
            raise RulesetError(tr("Invalid interface name: %s"), repr(name))
        return name

class InterfaceResource(Resource):
    XML_TAG = 'interface'
    TYPE = INTERFACE_RESTYPE
    name = Name(optional=True)

    # Group objects
    CHILD_CLASSES = (NetworkResource, HostResource, HostnameResource)

    def __init__(self, resources, attr, loader_context=None):
        Resource.__init__(self, resources, resources, self, attr, loader_context)

    def setAttributes(self, attr, is_modify):
        Resource.setAttributes(self, attr, is_modify)
        if self.name is None:
            self.type = GENERIC_INTERFACE_RESTYPE
        else:
            self.type = INTERFACE_RESTYPE

    def __unicode__(self):
        return tr('The %s interface') % self.formatID()

    def getAddressTypes(self):
        return set((INTERFACE_ADDRESS, IPV4_ADDRESS, IPV6_ADDRESS))

    def checkResource(self, new_resource, loader_context=None):
        if not isinstance(new_resource, (NetworkResource, NetworkGroup)):
            raise RulesetError(
                tr("The %s network can not be added to the %s interface!"),
                new_resource.formatID(), self.formatID())
        Resource.checkResource(self, new_resource, loader_context)

    def templatize(self, attr):
        attr['name'] = None

    def isGeneric(self, recursive=False):
        return (self.type == GENERIC_INTERFACE_RESTYPE)

    def setPhysical(self, name):
        self.name = name
        self.type = INTERFACE_RESTYPE

    def setGeneric(self):
        self.name = None
        self.type = GENERIC_INTERFACE_RESTYPE

    def _matchResource(self, other):
        return (other.interface == self)

    def _removeTemplate(self, action, template_name):
        Resource._removeTemplate(self, action, template_name)
        if self.isGeneric():
            self.ruleset.generic_links.removeTemplateAction(
                action, template_name, 'interfaces', self,
                tr('Unable to delete the template "%s": the generic interface %s is not defined'))

    def importXMLChildren(self, root, context, action):
        Resource.importXMLChildren(self, root, context, action)
        for node in root.findall(NetworkGroup.XML_TAG):
            NetworkGroup.importXML(self, node, context, action)

    def onModify(self, previous_state):
        # When an interface identifier changes, IPv4 and IPv6 rules create
        # special updates: see Acl.referentActionUpdates()
        old_id = previous_state['id']
        if self.id == old_id:
            return
        rules = self.ruleset.rules
        rules['acls-ipv4'].onInterfaceRename(self, old_id)
        rules['acls-ipv6'].onInterfaceRename(self, old_id)

