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

from ufwi_ruleset.forward.error import RulesetError
from ufwi_ruleset.forward.action import Action, ActionHandler, Update, Updates
from ufwi_ruleset.forward.object_set import ObjectSet, duplicateIdentifierError

class ObjectDict(dict, ObjectSet):
    def __init__(self, ruleset):
        dict.__init__(self)
        ObjectSet.__init__(self, ruleset)

    def createIdentifier(self, identifier):
        index = 1
        orig_identifier = identifier
        identifier_format = orig_identifier + "-%s"
        while True:
            if identifier not in self:
                break
            index += 1
            identifier = identifier_format % index
        return identifier

    def modifyObjectAction(self, object, new_attr):
        """
        Modify the object using an action.
        The result is the action which has already been executed.
        """
        old_id = object.id
        object.checkEditable()
        old_attr = object.getAttributes()
        new_id = new_attr['id']
        domain = object.update_domain

        if old_id != new_id:
            existing = self.get(new_id)
            if (existing is not None) and (existing is not object):
                duplicateIdentifierError(new_id)
            apply_updates = Updates(
                Update(domain, "delete", old_id),
                Update(domain, "create", new_id))
            unapply_updates = Updates(
                Update(domain, "delete", new_id),
                Update(domain, "create", old_id))
        else:
            apply_updates = Updates(Update(domain, "update", new_id))
            unapply_updates = apply_updates

        action = Action(
            ActionHandler(apply_updates, self._setattr, object, new_attr),
            ActionHandler(unapply_updates, self._setattr, object, old_attr))
        if old_id != new_id and object.original_id:
            set_original = Action(
                ActionHandler(apply_updates, self._set_original_id, object, None),
                ActionHandler(unapply_updates, self._set_original_id, object, object.original_id))
            action.chain(set_original)
        action.apply()
        if old_id != new_id:
            self._updateObjects(action, object.references, object, old_attr)
            self._updateObjects(action, object.getReferents())
        object.onModifyAction(action, old_attr)
        return action

    def _set_original_id(self, object, identifier):
        object.original_id = identifier

    def _rename(self, object, old_id, new_id):
        del self[old_id]
        self[new_id] = object

    def templatize(self, object, fusion):
        object.checkEditable()
        if object.isGeneric():
            raise RulesetError(
                tr("The %s object is already a generic object."),
                object.formatID())
        if not self.ruleset.is_template:
            raise RulesetError(tr("The rule set is not a template!"))
        attr = object.getAttributes()
        object.templatize(attr)
        return self.modifyObject(object, attr, fusion)

    def __repr__(self):
        return "<%s>" % self.__class__.__name__

    def add(self, object):
        self.checkIdentifierUnicity(object.id)
        dict.__setitem__(self, object.id.lower(), object)

    def __contains__(self, id):
        key = id.lower()
        return dict.__contains__(self, key)

    def __setitem__(self, id, object):
        key = id.lower()
        return dict.__setitem__(self, key, object)

    def __getitem__(self, identifier):
        key = identifier.lower()
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            raise RulesetError(tr("Unknown identifier: %s"), repr(identifier))

    def get(self, identifier, default=None):
        try:
            return self[identifier]
        except RulesetError:
            return default

    def __delitem__(self, key):
        if not isinstance(key, unicode):
            key = key.id.lower()
        key = key.lower()
        dict.__delitem__(self, key)

    def __iter__(self):
        return self.itervalues()

    def exportXMLRPC(self, fusion):
        for obj in self:
            yield obj.exportXMLRPC(fusion)

    def _renameAction(self, object, new_id, action):
        old_id = object.id
        old_attr = object.getAttributes()
        new_attr = dict(old_attr)
        new_attr['id'] = new_id

        domain = object.update_domain
        apply_updates = Updates(
            Update(domain, "delete", old_id),
            Update(domain, "create", new_id))
        unapply_updates = Updates(
            Update(domain, "delete", new_id),
            Update(domain, "create", old_id))

        set_action = Action(
            ActionHandler(apply_updates, self._setattr, object, new_attr),
            ActionHandler(unapply_updates, self._setattr, object, old_attr))
        action.executeAndChain(set_action)

        set_original = Action(
            ActionHandler(apply_updates, self._set_original_id, object, None),
            ActionHandler(unapply_updates, self._set_original_id, object, object.original_id))
        action.executeAndChain(set_original)

    def renameAction(self, object, new_id):
        new_attr = object.getAttributes()
        new_attr['id'] = new_id
        return self.modifyObjectAction(object, new_attr)

    def renameExisting(self, context, object):
        # Method called by Object.fromXML()
        old_id = object.id
        if old_id not in self:
            return
        new_id = self.createIdentifier(old_id)
        context.renameIdentifier(self.name, old_id, new_id)
        object.original_id = old_id
        object.id = new_id

    def normalizeIdentifier(self, identifier):
        return identifier.lower()

