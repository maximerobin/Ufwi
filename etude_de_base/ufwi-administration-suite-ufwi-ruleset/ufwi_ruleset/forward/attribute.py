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

from ufwi_rpcd.common.human import typeName
from ufwi_rpcd.backend.error import exceptionAsUnicode

class Attribute:
    """
    getter method allow to map class inheriting of Attribute with type
    For example :
        - class Integer -> int
        - class Comment -> unicode

    getter method can also be overridden (see rule)
    """
    type = None
    xmlrpc = None
    _index = 0

    def __init__(self, default=None, optional=False, const=False,
    xml="attr"):
        if default is not None:
            if (self.type is not None) \
            and not isinstance(default, self.type):
                raise TypeError(
                    "The attribute type is %s, whereas the default value type is %s" % (
                    self.type.__name__, typeName(default)))
            self.default = default
        elif not const:
            self.default = None
        else:
            raise ValueError("Constant attribute without value")
        if optional:
            self.optional = optional
        else:
            self.optional = (self.default is not None)
        self.const = const
        self.xml = xml
        self.index = Attribute._index
        Attribute._index += 1

    def getter(self, object, name, value):
        return self.type(value)

    def _get(self, object, name, value):
        try:
            value = self.getter(object, name, value)
        except Exception, err:
            raise ValueError("Attribute %s.%s error: %s" % (
                object.__class__.__name__, name, exceptionAsUnicode(err)))
        if value is not None \
        and not isinstance(value, self.type):
            raise TypeError("Attribute %s.%s type is %s, not %s" % (
                object.__class__.__name__, name,
                self.type.__name__, type(value).__name__))
        return value

    def get(self, object, data, name):
        if name not in data:
            if not self.optional:
                raise ValueError("Missing %s.%s attribute" % (
                    object.__class__.__name__, name))
            return self.default

        value = data.pop(name)
        if value is not None:
            value = self._get(object, name, value)
        if self.const:
            if (value is not None) \
            and (value != self.default):
                raise ValueError("Attribute %s.%s is constant" % (
                    object.__class__.__name__, name))
            return self.default
        if value is None:
            if self.optional:
                value = self.default
            else:
                raise ValueError("Missing %s.%s attribute" % (
                    object.__class__.__name__, name))
        return value

    def _readXML(self, library, node, name, context):
        if self.xml == "text":
            return node.text
        else: # xml == 'attr'
            return node.attrib.get(name)

    def readXML(self, library, node, name, context):
        if not self.xml:
            return None
        if self.const:
            return None
        return self._readXML(library, node, name, context)

    def exportXMLValue(self, value):
        return unicode(value)

    def _exportXML(self, node, name, value):
        value = self.exportXMLValue(value)
        if self.xml == "text":
            node.text = value
        else: # xml == 'attr'
            node.attrib[name] = value

    def exportXML(self, object, name, node):
        if not self.xml:
            return
        value = getattr(object, name)
        if value is None:
            return None
        if (self.default is not None) \
        and (value == self.default):
            # Ignore value equals to the default value to write shorter XML
            return None
        self._exportXML(node, name, value)

    def _exportXMLRPC(self, value, fusion):
        if self.xmlrpc:
            return self.xmlrpc(value)
        else:
            return value

    def exportXMLRPC(self, object, name, fusion):
        value = getattr(object, name)
        if value is None:
            return None
        return self._exportXMLRPC(value, fusion)

    def __repr__(self):
        attr = ['optional=%s' % self.optional]
        if self.default is not None:
            attr.append('default=%r' % self.default)
        return "<%s %s>" % (self.__class__.__name__, ' '.join(attr))

class Integer(Attribute):
    type = int

    def __init__(self, min, max=None, default=None, optional=False, const=False,
    xml="attr"):
        self.min = min
        self.max = max
        Attribute.__init__(self, default, optional, const, xml)

    def getter(self, object, name, value):
        if isinstance(value, (str, unicode)) and (not value):
            return None
        value = int(value)
        if (value < self.min) \
        or (self.max is not None and self.max < value):
            if self.max is not None:
                raise ValueError(
                    "Invalid value: %s.%s=%s, must be in range [%s; %s]" % (
                    object.__class__.__name__, name,
                    value, self.min, self.max))
            else:
                raise ValueError(
                    "Invalid value: %s.%s=%s, minimum value is %s" % (
                    object.__class__.__name__, name,
                    value, self.min))
        return value

def getUnicode(text):
    text = unicode(text)
    text = text.strip()
    if not text:
        return None
    return text

class Unicode(Attribute):
    type = unicode

    def getter(self, object, name, value):
        return getUnicode(value)

class Boolean(Unicode):
    type = bool

    def getter(self, object, name, value):
        if isinstance(value, (unicode, str)):
            value = Unicode.getter(self, object, name, value)
            if value is not None:
                return (value == u'1')
            else:
                return None
        else:
            return bool(value)

    def exportXMLValue(self, value):
        return unicode(int(value))

class Enum(Attribute):
    # Don't check the attribute type, only the value

    def __init__(self, enum, default=None, optional=False, const=False,
    xml="attr"):
        Attribute.__init__(self, default, optional, const, xml)
        if (enum is None) or len(enum) == 0:
            raise ValueError("enum is not set or an empty list")
        self.enum = set(enum)

    def getter(self, object, name, value):
        return value

    def _get(self, object, name, value):
        value = self.getter(object, name, value)
        if value not in self.enum:
            values = ', '.join(map(unicode, self.enum))
            raise TypeError("Attribute %s.%s value (%s) is not in %s"
                % (object.__class__.__name__, name, value, values))
        return value

class BaseObjectSet(Attribute):
    def _exportXMLRPC(self, objects, fusion):
        return [object.getID(fusion) for object in objects]

