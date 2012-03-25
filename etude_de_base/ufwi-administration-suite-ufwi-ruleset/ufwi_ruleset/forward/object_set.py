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

def duplicateIdentifierError(identifier):
    raise RulesetError(tr('The "%s" identifier is already used!'), identifier)

class ObjectSet(object):
    """
    Base class of abstract classes ObjectDict and Rules.

    Store objects of type Object (or a subclass).
    """
    NAME = None
    def __init__(self, ruleset):
        self.name = self.NAME
        self.ruleset = ruleset

    def _setattr(self, object, new_attr):
        # Set objet new attribute on a modification (not on creation)

        # Keep existing attributes, so it's possible to modify objects an old
        # client on a newer server without losing attributes. Eg. the server
        # has an auth_quality field, whereas the client doesn't support (know)
        # it.
        attr = object.getAttributes()
        attr.update(new_attr)

        # set new attributes
        old_id = object.id
        old_referents = set(object.getReferents())
        object.init(attr)
        new_referents = set(object.getReferents())
        new_id = object.id

        # update references
        for removed in old_referents - new_referents:
            removed.removeReference(object)
        for added in new_referents - old_referents:
            added.addReference(object)

        # update indexes if the identifier changed
        if old_id != new_id:
            if self.normalizeIdentifier(old_id) != self.normalizeIdentifier(new_id):
                self.checkIdentifierUnicity(new_id)
            self._rename(object, old_id, new_id)

    def _updateObjects(self, action, objects, referent=None, old_attr=None):
        # referent and old_attr are only defined if objects are references of
        # referent.  Otherwise, referent is None
        for object in objects:
            if referent:
                object.referentActionUpdates(action, referent, old_attr)
            else:
                update = object.createUpdate()
                action.addBothUpdate(update)

    def removeTemplate(self, action, name):
        # Copy items because the set may changes during the operation
        items = list(self)
        for obj in items:
            obj.removeTemplate(action, name)

    def modifyObject(self, object, new_attr, fusion):
        action = self.modifyObjectAction(object, new_attr)
        self.ruleset.updateFusion(action, fusion)
        return self.ruleset.addAction(action, apply=False)

    def checkIdentifierUnicity(self, identifier):
        if identifier in self:
            duplicateIdentifierError(identifier)

    def normalizeIdentifier(self, identifier):
        return identifier

    def createObject(self, attr, fusion):
        action = self.createObjectAction(attr)
        action.apply()
        self.ruleset.updateFusion(action, fusion)
        return self.ruleset.addAction(action, apply=False)

    # --- abstract methods ---

    @abstractmethod
    def modifyObjectAction(self, object, new_attr):
        pass

    @abstractmethod
    def _rename(self, object, old_id, new_id):
        pass

    @abstractmethod
    def __contains__(self, identifier):
        pass

    @abstractmethod
    def __getitem__(self, aclid):
        pass

    @abstractmethod
    def _create(self, object):
        pass

    @abstractmethod
    def createObjectAction(self, attr):
        pass

