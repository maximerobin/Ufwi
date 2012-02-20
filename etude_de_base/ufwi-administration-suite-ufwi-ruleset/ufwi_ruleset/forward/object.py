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
from ufwi_rpcd.common.odict import odict
from ufwi_rpcd.common.xml_etree import etree
from ufwi_rpcd.common.tools import abstractmethod

from ufwi_ruleset.forward.attribute import Attribute, Unicode, Boolean
from ufwi_ruleset.common.regex import IDENTIFIER_REGEX_STR
from ufwi_ruleset.forward.error import RulesetError
from ufwi_ruleset.forward.action import Action, ActionHandler, Update

REGEX_ID = re.compile(IDENTIFIER_REGEX_STR)

def checkIdentifier(id):
    if not isinstance(id, unicode):
        raise RulesetError(tr("Invalid identifier: type is not unicode (%s)"), unicode(type(id)))
    if not id:
        raise RulesetError(tr("Invalid identifier: empty string"))
    if not REGEX_ID.match(id):
        raise RulesetError(tr("Invalid identifier: invalid characters or length (%s)"), repr(id))

class Identifier(Unicode):
    def getter(self, object, name, value):
        value = Unicode.getter(self, object, name, value)
        checkIdentifier(value)
        return value

class Object(object):
    XML_TAG = None
    UPDATE_DOMAIN = None

    id = Identifier(xml="text")
    editable = Boolean(True, xml=False)

    def __init__(self, data, loader_context=None):
        self.update_domain = self.UPDATE_DOMAIN
        self.references = set()
        # original identifier in the XML file, it should not be used in XML-RPC
        self.original_id = None
        # name of the template, or None
        self.from_template = data.pop('from_template', None)
        self.physical_object = None
        self._attributes = Object._createAttributes(self.__class__)
        self.init(data, loader_context, is_modify=False)

    def onLoading(self, loader_context):
        # Method called when an object is loaded from a ruleset file.
        # It's used to get backward compatibility: fix attributes after
        # loading an old ruleset.
        pass

    def init(self, data, loader_context=None, is_modify=True):
        """
        Write the attribute values and check object consistency. The
        operation is atomic: restore old attributes on error.
        """
        previous_state = dict(self.__dict__)
        if is_modify:
            old_attr = self.getAttributes()
        try:
            data = dict(data)
            self.setAttributes(data, is_modify)
            keys = data.keys()
            if keys:
                raise RulesetError(
                    tr("Unknown attributes: %s"),
                    u', '.join(keys))
            if loader_context:
                self.onLoading(loader_context)
            if is_modify:
                self.onModify(old_attr)
            self.checkConsistency(loader_context)
            if is_modify:
                for reference in self.references:
                    reference.checkConsistency(loader_context)
        except:
            # Restore previous (valid) state on error
            self.__dict__ = previous_state
            raise

    def onModify(self, previous_state):
        # call by init() on modification
        pass

    def onModifyAction(self, action, old_attr):
        # call by ObjectDict.modifyObjectAction()
        pass

    def checkConsistency(self, loader_context=None):
        # raise an error if the object is inconsistent
        pass

    @staticmethod
    def _createAttributes(cls):
        attributes = []
        for name in dir(cls):
            attr = getattr(cls, name)
            if not isinstance(attr, Attribute):
                continue
            attributes.append((name, attr))
        attributes.sort(key=lambda(name,attr): attr.index)
        return odict(attributes)

    def setAttributes(self, data, is_modify):
        for name, attr in self._attributes.iteritems():
            value = attr.get(self, data, name)
            setattr(self, name, value)

    @classmethod
    def fromXML(cls, library, attr, context, action):
        """
        create an object from a dict
            attr: dict of attrs
            if action is not None, undoing creation will be possible
        """
        object = cls(library, attr, context)
        library.renameExisting(context, object)
        if action:
            create = library._createAction(object)
            action.executeAndChain(create)
        else:
            library._create(object)
        return object

    @classmethod
    def importXML(cls, library, node, context, action):
        """
        create a dict from a XML node and return an object
        """
        data = {}
        attributes = Object._createAttributes(cls)
        for name, attr in attributes.iteritems():
            value = attr.readXML(library, node, name, context)
            if value is None:
                continue
            data[name] = value
        data['editable'] = context.editable
        data['from_template'] = context.from_template
        # FIXME: importXML should not return the object
        return cls.fromXML(library, data, context, action)

    def exportXML(self, parent):
        node = etree.SubElement(parent, self.XML_TAG)
        if self.original_id:
            new_id = self.id
            self.id = self.original_id
        for name, attr in self._attributes.iteritems():
            attr.exportXML(self, name, node)
        if self.original_id:
            self.id = new_id
        return node

    def getAttributes(self, fusion=False, use_none=True):
        """
        Get attributes. If fusion is True, get physical object identifier for
        generic objects (see Object.getID() method).

        Return a dictionary: attribute name (str) => value (type depends on the
        attribute).
        """
        attr = {}
        for name, attrobj in self._attributes.iteritems():
            value = attrobj.exportXMLRPC(self, name, fusion)
            if (not use_none) and (value is None):
                continue
            attr[name] = value
        return attr

    def exportXMLRPC(self, fusion):
        attr = self.getAttributes(fusion, use_none=False)
        references = [(object.update_domain, object.id) for object in self.references]
        references.sort()
        attr['references'] = references
        try:
            attr['address_types'] = list(self.getAddressTypes())
        except NotImplementedError:
            pass
        if self.from_template:
            attr['from_template'] = self.from_template
        if self.physical_object:
            attr['physical_id'] = self.physical_object.id
        return attr

    def addReference(self, object):
        self.references.add(object)

    def removeReference(self, object):
        self.references.remove(object)

    def checkEditable(self):
        if self.editable:
            return
        raise RulesetError(tr('The %s object is not editable!') % self.formatID())

    def getID(self, fusion):
        if fusion and self.physical_object:
            return self.physical_object.id
        else:
            return self.id

    def getOriginalID(self):
        """
        Original identifier in the XML file, it should not be used in XML-RPC.
        """
        if self.original_id:
            return self.original_id
        else:
            return self.id

    def formatID(self):
        return '"%s"' % self.id

    def __repr__(self):
        text = self.__class__.__name__
        if not issubclass(self.id.__class__, Attribute):
            id_ascii = unicode(self.id)
            id_ascii = id_ascii.encode('ASCII', 'backslashreplace')
            text += ' id=%r' % id_ascii
        else:
            text += '@0x%x' % id(self)
        return '<%s>' % text

    def __str__(self):
        text = self.__unicode__()
        return text.encode('ASCII', 'backslashreplace')

    # Don't export references to pickle (serialization)
    def __getstate__(self):
        state = dict(self.__dict__)
        del state['references']
        return state
    def __setstate__(self, state):
        state['references'] = set()
        self.__dict__ = state

    def __nonzero__(self):
        # "if attr: ..." is always True
        return True

    def getReferents(self):
        return set()

    def registerReferences(self):
        for object in self.getReferents():
            object.addReference(self)

    def unregisterReferences(self):
        for object in self.getReferents():
            object.removeReference(self)

    def isGeneric(self, recursive=False):
        return False

    def templatize(self, attr):
        raise RulesetError(tr("The %s object can not be templatized."), self.formatID())

    def _setTemplate(self, name):
        self.from_template = name
        self.editable = False

    def _unsetTemplate(self):
        self.from_template = None
        self.editable = True

    def createUpdate(self):
        return Update(self.update_domain, "update", self.id)

    def referentActionUpdates(self, action, referent, old_attr):
        update = self.createUpdate()
        action.addBothUpdate(update)

    def _removeTemplate(self, action, name):
        update = self.createUpdate()
        new_action = Action(
            ActionHandler(update, self._unsetTemplate),
            ActionHandler(update, self._setTemplate, name))
        action.executeAndChain(new_action)

    def removeTemplate(self, action, name):
        if self.from_template != name:
            return
        self._removeTemplate(action, name)

    def overlaps(self, other):
        return self.match(other) or other.match(self)

    #--- Abstract methods ---------------------

    @abstractmethod
    def __unicode__(self):
        pass

    @abstractmethod
    def getAddressTypes(self):
        pass

    @abstractmethod
    def setPhysical(self, physical):
        pass

    @abstractmethod
    def setGeneric(self):
        pass

    @abstractmethod
    def match(self, other):
        pass

