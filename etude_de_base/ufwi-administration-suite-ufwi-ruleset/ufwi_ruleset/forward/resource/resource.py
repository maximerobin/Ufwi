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
from ufwi_rpcd.common.tools import abstractmethod

from ufwi_ruleset.forward.object import Object, Identifier
from ufwi_ruleset.forward.resource import ResourcesContainer

class Resource(Object, ResourcesContainer):
    UPDATE_DOMAIN = u'resources'
    SUBCLASSES = []

    # abstract class attributes
    TYPE = None
    XML_TAG = None

    id = Identifier()

    def __init__(self, resources, parent, interface, attr, loader_context=None):
        ResourcesContainer.__init__(self, resources)
        self.type = self.TYPE        # Resource type
        self.parent = parent         # Resource
        self.interface = interface   # InterfaceResource
        self.children = []           # list of Resource
        Object.__init__(self, attr, loader_context)

    def checkConsistency(self, loader_context=None):
        self.parent.checkResource(self, loader_context)
        for child in self.iterChildren():
            child.checkConsistency(loader_context)

    def exportXMLRPC(self, fusion):
        data = Object.exportXMLRPC(self, fusion)
        data['type'] = self.type
        data['allow_child'] = self.allow_child
        data['interface'] = self.interface.id
        data['is_generic'] = self.isGeneric()
        if self.parent and issubclass(self.parent.__class__, Resource):
            data['parent'] = self.parent.id

        children = []
        for child in self.iterChildren():
            children.append(child.exportXMLRPC(fusion))
        if children:
            data['children'] = children
        return data

    def __hash__(self):
        return hash(self.id)

    def exportXML(self, parent):
        children = self.getChildren()
        if self.from_template:
            node = etree.SubElement(parent, self.XML_TAG, reference=self.id)
            remove_empty = True
        else:
            node = Object.exportXML(self, parent)
            remove_empty = False
        children.sort(key=lambda resource: resource.id)
        empty = True
        for child in children:
            if child.exportXML(node) is not None:
                empty = False
        if remove_empty and empty:
            parent.remove(node)
            return None
        return node

    @classmethod
    def registerSubclass(cls, subclass):
        cls.SUBCLASSES.append(subclass)

    def isInternet(self):
        """
        Is an Internet resource? Eg. the network "0.0.0.0/0".
        """
        return False

    def iterChildren(self, recursive=False):
        """
        Iterate on direct children.
        Use iter(self.resources) to iterate on all networks.
        """
        for network in self.children:
            yield network
            if recursive:
                for child in network.iterChildren(recursive):
                    yield child

    def renameExisting(self, context, object):
        self.resources.renameExisting(context, object)

    def renameAction(self, object, new_id):
        return self.resources.renameAction(object, new_id)

    def _create(self, network):
        self.resources._create(network)
        self.children.append(network)

    def _delete(self, network):
        self.resources._delete(network)
        self.children.remove(network)

    def match(self, other):
        if not isinstance(other, Resource):
            return False
        if self.interface != other.interface:
            return False
        return self._matchResource(other)

    def hasAddresses(self):
        return False

    # --- abstract methods ----------------------------------------

    @abstractmethod
    def getAddresses(self):
        pass

    @abstractmethod
    def _matchResource(self, other):
        pass

