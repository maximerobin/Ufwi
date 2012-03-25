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
from ufwi_rpcd.common.tools import getFirst

from ufwi_ruleset.forward.object import Object, Identifier
from ufwi_ruleset.forward.attribute import BaseObjectSet
from ufwi_ruleset.forward.tools import getIdentifier


class ObjectList(BaseObjectSet):
    def getter(self, group, name, identifier):
        return group.library[identifier]

    def _get(self, object, name, identifiers):
        identifiers = set(identifiers)
        values = []
        for item in identifiers:
            value = self.getter(object, name, item)
            if value is None:
                raise TypeError(
                    "Attribute %s.%s list contains an invalid value: %s" % (
                    object.__class__.__name__, name,
                    repr(item)))
            values.append(value)
        if not values:
            return None
        return values

    def _readXML(self, library, group_node, name, context):
        identifiers = []
        for child_class in library.CHILD_CLASSES:
            for node in group_node.findall(child_class.XML_TAG):
                identifier = node.text
                identifier = context.getIdentifier(library.name, identifier)
                identifiers.append(identifier)
        return identifiers

    def _exportXML(self, node, name, values):
        values = list(values)
        values.sort(key=getIdentifier)
        for item in values:
            sub_node = etree.SubElement(node, item.XML_TAG)
            sub_node.text = item.getOriginalID()

class Group(Object):
    XML_TAG = u"group"
    id = Identifier()
    objects = ObjectList()

    def __init__(self, library, values, loader_context=None):
        self.library = library
        Object.__init__(self, values, loader_context)
        self.update_domain = getFirst(self.objects).update_domain

    def isGeneric(self, recursive=False):
        if recursive:
            return any(object.isGeneric(recursive) for object in self.objects)
        else:
            return False

    def __unicode__(self):
        return tr("The group %s") % self.formatID()

    def getReferents(self):
        return set(self.objects)

    def getAddressTypes(self):
        address_types = None
        for object in self.objects:
            if address_types is not None:
                address_types &= object.getAddressTypes()
            else:
                address_types = object.getAddressTypes()
        return address_types

