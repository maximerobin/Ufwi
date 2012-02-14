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

from ufwi_rpcd.common.xml_etree import etree

from ufwi_rpcd.common import tr

from ufwi_ruleset.common.network import (
    INTERFACE_RESTYPE, GENERIC_INTERFACE_RESTYPE,
    NETWORK_RESTYPE, GENERIC_NETWORK_RESTYPE,
    IPSEC_NETWORK_RESTYPE,
    HOST_RESTYPE, GENERIC_HOST_RESTYPE)

from ufwi_ruleset.forward.error import RulesetError
from ufwi_ruleset.forward.object_dict import ObjectDict
from ufwi_ruleset.forward.action import Action, ActionHandler, Update
from ufwi_ruleset.forward.resource import (ResourcesContainer,
    InterfaceResource, FirewallResource, NetworkGroup,
    NetworkResource, IPsecNetworkResource, HostResource, HostnameResource)


class Resources(ObjectDict, ResourcesContainer):
    NAME = "resources"

    # Resources contains also a FirewallObject, but it's not loaded
    # from XML, so it's not registered in SUBCLASSES
    SUBCLASSES = (InterfaceResource,)

    def __init__(self, ruleset):
        ObjectDict.__init__(self, ruleset)
        ResourcesContainer.__init__(self, self, ruleset)

    def iterChildren(self, recursive=False):
        for network in self.itervalues():
            if (not recursive) and (network.parent is not self):
                continue
            yield network

    def getXMLReference(self, identifier):
        try:
            return self[identifier]
        except RulesetError:
            raise RulesetError(tr('Broken XML reference: "%s"!'), identifier)

    def exportXML(self, root):
        node = etree.SubElement(root, "resources")
        interfaces = self.getChildren()
        interfaces.sort(key=lambda interface: interface.id)
        empty = True
        for interface in interfaces:
            if interface.exportXML(node) is not None:
                empty = False
        if empty:
            root.remove(node)

    def importXML(self, root, context, action):
        resources = root.find('resources')
        if resources is None:
            return
        self.importXMLChildren(resources, context, action)

    def checkResource(self, new_resource, loader_context=None):
        ResourcesContainer.checkResource(self, new_resource, loader_context)
        assert isinstance(new_resource, InterfaceResource) or isinstance(new_resource, FirewallResource)

    def _create(self, network):
        # Check consistency
        parent = network.parent
        if not parent.allow_child:
            raise RulesetError(
                tr("You can not add a child to the %s network!"),
                self.formatID())
        self.checkIdentifierUnicity(network.id)

        # Register the network
        self[network.id] = network
        if isinstance(network, NetworkGroup):
            network.registerReferences()

    def _delete(self, network):
        if isinstance(network, NetworkGroup):
            network.unregisterReferences()
        del self[network.id]

    def __repr__(self):
        return "<Resources>"

    def mergeNetworks(self, networks, network_dict=None):
        network_dict = {}
        merge_children = []
        merge_references = []
        self._mergeNetworks(networks, network_dict, merge_children, merge_references)
        for physical_id, children in merge_children:
            physical = network_dict[physical_id]
            if 'children' not in physical:
                physical['children'] = []
            physical['children'].extend(children)
        for physical_id, references in merge_references:
            physical = network_dict[physical_id]
            physical['references'].extend(references)

    def _mergeNetworks(self, networks, network_dict,
    merge_children, merge_references):
        delete = []
        for index, network in enumerate(networks):
            if 'physical_id' in network:
                physical_id = network['physical_id']
                if 'children' in network:
                    merge_children.append((physical_id, network['children']))
                if 'references' in network:
                    merge_references.append((physical_id, network['references']))
                delete.append(index)
            else:
                network_dict[network['id']] = network
            if 'children' in network:
                self._mergeNetworks(network['children'], network_dict,
                    merge_children, merge_references)
        for index in reversed(delete):
            del networks[index]

    def exportXMLRPC(self, fusion):
        interfaces = (interface.exportXMLRPC(fusion) for interface in self.iterChildren())
        if not fusion:
            return interfaces
        interfaces = list(interfaces)
        self.mergeNetworks(interfaces)
        return interfaces

    def formatID(self):
        return u"<Resources>"

    def getInterfaceByName(self, name):
        for interface in self.iterChildren():
            if not isinstance(interface, InterfaceResource):
                continue
            if interface.name == name:
                return interface
        return None

    def createGroup(self, attr):
        group = NetworkGroup(self, attr)
        domain = group.update_domain
        parent = group.parent
        action = Action(
            ActionHandler(Update(domain, "create", group.id), parent._create, group),
            ActionHandler(Update(domain, "delete", group.id), parent._delete, group))
        self._updateObjects(action, group.getReferents())
        return self.ruleset.addAction(action)

    def serviceCreate(self, restype, parent, attr, fusion):
        if restype in (INTERFACE_RESTYPE, GENERIC_INTERFACE_RESTYPE):
            parent = self
            network = InterfaceResource(self, attr)
        else:
            parent = self[parent]
            if restype in (NETWORK_RESTYPE, GENERIC_NETWORK_RESTYPE):
                network = NetworkResource(parent, attr)
            elif restype == IPSEC_NETWORK_RESTYPE:
                network = IPsecNetworkResource(parent, attr)
            elif restype in (HOST_RESTYPE, GENERIC_HOST_RESTYPE):
                network = HostResource(parent, attr)
            else:
                # restype == HOSTNAME_RESTYPE
                network = HostnameResource(parent, attr)
        return parent.createResource(network, fusion)

