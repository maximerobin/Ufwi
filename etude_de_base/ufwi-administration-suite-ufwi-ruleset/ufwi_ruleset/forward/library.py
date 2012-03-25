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
from ufwi_rpcd.common.xml_etree import etree

from ufwi_ruleset.forward.object_dict import ObjectDict
from ufwi_ruleset.forward.action import Action, ActionHandler, Update, Updates
from ufwi_ruleset.forward.error import RulesetError
from ufwi_ruleset.forward.group import Group

class Library(ObjectDict):
    ACL_ATTRIBUTE = None
    XML_TAG = None
    CHILD_CLASSES = None

    def _create(self, object):
        if object.isGeneric() \
        and (not object.from_template) \
        and (not self.ruleset.is_template):
            raise RulesetError(tr("The rule set is not a template!"))
        object.registerReferences()
        self.add(object)
        return object

    def _delete(self, object):
        object.unregisterReferences()
        del self[object]

    def _createAction(self, object):
        domain = object.update_domain
        action = Action(
            ActionHandler(Update(domain, "create", object.id), self._create, object),
            ActionHandler(Update(domain, "delete", object.id), self._delete, object))
        return action

    def delete(self, identifier):
        # Get the object
        object = self[identifier]
        object.checkEditable()

        # The object is still used?
        if object.references:
            objects = u', '.join(object.formatID() for object in object.references)
            raise RulesetError(
                tr("Unable to delete the %s object: it is used by the %s objects!"),
                object.formatID(), objects)

        domain = object.update_domain
        apply_updates = Updates(Update(domain, "delete", identifier))
        unapply_updates = Updates(Update(domain, "create", identifier))

        # Create and apply the action
        action = Action(
            ActionHandler(apply_updates, self._delete, object),
            ActionHandler(unapply_updates, self._create, object))
        self._updateObjects(action, object.getReferents())
        return self.ruleset.addAction(action)

    def _createObject(self, attr):
        if len(self.CHILD_CLASSES) != 1:
            raise NotImplementedError()
        cls = self.CHILD_CLASSES[0]
        return cls(self, attr)

    def createObjectAction(self, attr):
        if 'from_template' in attr:
            # from_template is not user controlable
            del attr['from_template']
        attr['editable'] = True
        obj = self._createObject(attr)
        return self._createAction(obj)

    def exportXML(self, root):
        objects = [object for object in self if object.editable]
        if not objects:
            return
        node = etree.SubElement(root, self.XML_TAG)
        objects.sort(key=lambda object: object.id)
        for object in objects:
            object.exportXML(node)
        return node

    def createGroup(self, attr):
        group = Group(self, attr)
        domain = group.update_domain
        action = Action(
            ActionHandler(Update(domain, "create", group.id), self._create, group),
            ActionHandler(Update(domain, "delete", group.id), self._delete, group))
        self._updateObjects(action, group.getReferents())
        return self.ruleset.addAction(action)

    def importXML(self, root, context, action):
        nodes = root.find(self.XML_TAG)
        if nodes is None:
            return
        for child_class in self.CHILD_CLASSES:
            child_tag = child_class.XML_TAG
            for node in nodes.findall(child_tag):
                child_class.importXML(self, node, context, action)
        for node in nodes.findall(Group.XML_TAG):
            Group.importXML(self, node, context, action)

