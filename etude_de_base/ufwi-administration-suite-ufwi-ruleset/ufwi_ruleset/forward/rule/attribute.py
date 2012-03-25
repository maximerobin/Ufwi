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
from ufwi_rpcd.common.human import typeName
from ufwi_rpcd.backend import tr

from ufwi_ruleset.forward.error import RulesetError
from ufwi_ruleset.forward.attribute import BaseObjectSet, Unicode, Integer
from ufwi_ruleset.forward.tools import getIdentifier

MAX_COMMENT_LENGTH = 500

class Identifier(Integer):
    def __init__(self):
        Integer.__init__(self, min=1)

    def _readXML(self, rules, node, name, context):
        if context.version in ("3.0m3", "3.0dev4"):
            return rules.createID() // 10
        identifier = Integer._readXML(self, rules, node, name, context)
        identifier = int(identifier)
        return identifier

    def exportXMLValue(self, value):
        return unicode(value // 10)

    def getter(self, object, name, value):
        value = Integer.getter(self, object, name, value)
        if value < 1:
            raise ValueError('Invalid value for the "%s" identifier: %s' % repr(value))
        return value

class Comment(Unicode):
    def _readXML(self, library, node, name, context):
        comment = node.find("comment")
        if comment is None:
            return None
        return comment.text

    def _exportXML(self, parent, name, value):
        value = self.exportXMLValue(value)
        node = etree.SubElement(parent, "comment")
        node.text = value

    def getter(self, rule, name, comment):
        comment = Unicode.getter(self, rule, name, comment)
        if comment is None:
            return None
        if MAX_COMMENT_LENGTH < len(comment):
            raise RulesetError(
                tr("The comment is too long (%s characters), the maximum is %s characters!"),
                len(comment), MAX_COMMENT_LENGTH)
        for character in comment:
            code = ord(character)
            if (32 <= code) or (code == 10):
                continue
            raise RulesetError(
                tr("Invalid character in the comment: %s (code %s)"),
                repr(character), code)
        return comment

class ObjectSet(BaseObjectSet):
    type = set

    def __init__(self, library_name, xmltag=None, optional=False):
        BaseObjectSet.__init__(self, optional=optional, xml="tag")
        self.library_name = library_name
        if xmltag is not None:
            self.xmltag = xmltag
        else:
            self.xmltag = library_name[:-1]   # 'applications' => 'application'

    def getter(self, rule, name, identifiers):
        if not isinstance(identifiers, (tuple, list)):
            raise TypeError("Attribute %r value is a tuple or list, not a %s"
                % (name, typeName(identifiers)))
        if not identifiers:
            if self.optional:
                return set()
            else:
                return None
        items = set()
        library = getattr(rule.ruleset, self.library_name)
        for identifier in identifiers:
            item = library[identifier]
            items.add(item)
        return items

    def get(self, object, data, name):
        value = BaseObjectSet.get(self, object, data, name)
        if value is not None:
            return value
        else:
            return set()

    def _readXML(self, library, parent_node, name, context):
        identifiers = []
        for node in parent_node.findall(self.xmltag):
            identifier = node.text
            identifier = context.getIdentifier(self.library_name, identifier)
            identifiers.append(identifier)
        return identifiers

    def _exportXML(self, node, name, values):
        values = list(values)
        values.sort(key=getIdentifier)
        for item in values:
            sub_node = etree.SubElement(node, self.xmltag)
            sub_node.text = item.getOriginalID()

