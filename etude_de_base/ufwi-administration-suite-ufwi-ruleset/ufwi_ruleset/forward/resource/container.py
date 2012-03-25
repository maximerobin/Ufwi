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
from ufwi_rpcd.common.tools import abstractmethod

from ufwi_ruleset.forward.error import RulesetError
from ufwi_ruleset.forward.object_set import duplicateIdentifierError
from ufwi_ruleset.forward.action import Action, ActionHandler, Update

class ResourcesContainer:
    SUBCLASSES = None

    def __init__(self, resources, ruleset=None):
        self.resources = resources
        if ruleset:
            self.ruleset = ruleset
        else:
            self.ruleset = resources.ruleset
        self.allow_child = True

    def checkIdentifierUnicity(self, identifier):
        if identifier in self.resources:
            duplicateIdentifierError(identifier)

    def checkResource(self, new_resource, loader_context=None):
        if new_resource.isGeneric():
            return
        interface = new_resource.interface
        interface.checkUnicity(new_resource, loader_context)

    def checkUnicity(self, new_resource, loader_context=None):
        for resource in self.iterChildren():
            if resource is new_resource:
                # on modify, don't check unicity
                continue
            resource.checkUnicity(new_resource, loader_context)

    def _createAction(self, network):
        apply_updates = Update("resources", "create", network.id)
        unapply_updates = Update("resources", "delete", network.id)
        return Action(
            ActionHandler(apply_updates, self._create, network),
            ActionHandler(unapply_updates, self._delete, network))

    def createResource(self, network, fusion):
        action = self._createAction(network)
        action.apply()
        self.ruleset.updateFusion(action, fusion)
        return self.ruleset.addAction(action, apply=False)

    def getChildren(self, recursive=False):
        return list(self.iterChildren(recursive))

    def delete(self, identifier):
        # FIXME: Factorize into Library.delete()

        # Get the resource
        resource = self.resources[identifier]
        resource.checkEditable()

        # Get all references
        resources = [resource] + resource.getChildren(recursive=True)
        for resource in resources:
            if not resource.references:
                continue
            # FIXME: avoid unicode(object)
            references = ', '.join(unicode(ref) for ref in resource.references)
            raise RulesetError(
                tr('Unable to delete the "%s" network: it is used by %s!'),
                resource.id, references)

        # Create the action
        identifiers = [ resource.id for resource in resources ]
        apply_updates = Update(u"resources", "delete", *identifiers)
        unapply_updates = Update(u"resources", "create", *identifiers)
        action = Action(
            ActionHandler(apply_updates, self._deleteMany, resources),
            ActionHandler(unapply_updates, self._createMany, resources))

        # Apply the action
        return self.ruleset.addAction(action)

    def _createMany(self, resources):
        for resource in resources:
            resource.parent._create(resource)

    def _deleteMany(self, resources):
        for resource in resources:
            resource.parent._delete(resource)

    def getType(self):
        return self.__class__.__name__

    # FIXME: inline this code in fromXML() or importXML()
    def importXMLChildren(self, root, context, action):
        for cls in self.SUBCLASSES:
            for node in root.findall(cls.XML_TAG):
                if 'reference' in node.attrib:
                    network = cls.importXMLReference(self, node, context)
                else:
                    network = cls.importXML(self, node, context, action)
                network.importXMLChildren(node, context, action)

    @classmethod
    def importXMLReference(cls, parent, node, context):
        identifier = unicode(node.attrib['reference'])
        network = parent.resources.getXMLReference(identifier)
        return network

    def getNetworkByAddress(self, address):
        for network in self.iterChildren():
            found = network.getNetworkByAddress(address)
            if found is not None:
                return found
        return None

    def getHostByAddress(self, address):
        for network in self.iterChildren():
            found = network.getHostByAddress(address)
            if found is not None:
                return found
        return None

    # --- abstract methods ----

    @abstractmethod
    def formatID(self):
        pass

    @abstractmethod
    def _create(self, resource):
        pass

    @abstractmethod
    def _delete(self, resource):
        pass

    @abstractmethod
    def iterChildren(self, recursive=False):
        pass

    @abstractmethod
    def renameAction(self, object, new_id):
        pass

    @abstractmethod
    def renameExisting(self, context, object):
        pass

