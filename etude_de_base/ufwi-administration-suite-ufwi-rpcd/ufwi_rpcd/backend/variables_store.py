
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

from __future__ import with_statement
from os import umask
from xml.sax.saxutils import escape, unescape

from ufwi_rpcd.common.xml_etree import save as xml_save, etree as ET
from ufwi_rpcd.common.error import exceptionAsUnicode

from ufwi_rpcd.backend import tr
from ufwi_rpcd.backend.exceptions import ConfigError
from ufwi_rpcd.backend.value import Value
from ufwi_rpcd.backend.error import (CONFIG_ERR_XML_READ,
    CONFIG_ERR_XML_WRITE, CONFIG_NO_SUCH_KEY, CONFIG_VALUE_DELETED,
    CONFIG_PATH_TOO_LONG, CONFIG_NO_SUCH_FILE)

VERSION = '1'

CONFIG_ROOT_TAG = 'edenwall'
CONFIG_ELT_TAG = 'config_elt'
DELETED_KEY_TAG = 'deleted_key'
DATA_TAG = 'data'

VERSION_ATTR = 'version'
NAME_ATTR = 'name'
TYPE_ATTR = 'type'

class VariablesStore(dict):
    def __init__(self):
        dict.__init__(self)
        self.deleted_keys = set()

    def __isempty__(self):
        return not self.__nonzero__()

    def __nonzero__(self):
        return len(self) != 0 or len(self.deleted_keys) != 0

    def __setitem__(self, key, value):
        if not isinstance(value, (self.__class__, Value)):
            try:
                value = Value(value)
            except TypeError:
                if isinstance(value, dict) and len(value) == 0:
                    value = self.__class__()

        dict.__setitem__(self, key, value)

    def __getitem__(self, *path_and_value):
        key = path_and_value[0]
        if len(path_and_value) > 2:
            return self[key].__setitem__(path_and_value[1:])
        try:
            value = dict.__getitem__(self, key)
        except KeyError:
            raise ConfigError(CONFIG_NO_SUCH_KEY,
                tr("No such key: %s"), unicode(key))
        if isinstance(value, Value):
            value = value.value
        return value

    def _getRaw(self, *path_and_value):
        key = path_and_value[0]
        if len(path_and_value) > 2:
            return self[key].__setitem__(path_and_value[1:])
        try:
            value = dict.__getitem__(self, key)
        except KeyError:
            raise ConfigError(CONFIG_NO_SUCH_KEY, tr("No such key: %s"), key)
        return value

    def set(self, *path_and_value):
        key = path_and_value[0]
        if len(path_and_value) > 2:
            return self.alwaysGet(key).set(*path_and_value[1:])
        value = path_and_value[-1]

        if isinstance(value, list):
            raise ConfigError(CONFIG_NO_SUCH_KEY, tr("Cannot set a list as a value"))

        if isinstance(value, dict) and value:
            #[len(value) > 0]
            self.fromDict(key, value)
            return
        self[key] = value

    def get(self, *path_and_value):

        path_len = len(path_and_value)
        if path_len == 0:
            value = self
        elif path_len == 1:
            value = self[ path_and_value[0] ]
            if isinstance(value, Value):
                return value.value
        else:
            return self[ path_and_value[0] ].get(*path_and_value[1:])

        if isinstance(value, self.__class__):
            return value.toDict()
        return value

    def fromDict(self, key, dictionnary):
        for subkey, value in dictionnary.iteritems():
            self.set(key, subkey, value)

    def clear(self):
        dict.clear(self)
        self.deleted_keys.clear()

    def delete(self, *path_and_value):
        key = path_and_value[0]
        if len(path_and_value) >= 2:
            return self[key].delete(*path_and_value[1:])
        self.deleted_keys.add(key)
        if key in self:
            del self[key]

    __delete__ = delete

    def iterpaths(self):
        for key, value in self.iteritems():
            if isinstance(value, self.__class__):
                yield key
                for path in value.iterpaths():
                    yield "%s/%s" % (key, path)

    def alwaysGet(self, key):
        if not key in self:
            self[key] = self.__class__()
        return self[key]

    def override(self, other_configuration, propagate_deleted_keys=True):

        for key in self.deleted_keys:
            if key in other_configuration:
                del other_configuration[key]
        if propagate_deleted_keys:
            other_configuration.deleted_keys |= self.deleted_keys

        for key, value in self.iteritems():

            if key not in other_configuration:
                other_configuration[key] = self[key]

            elif isinstance(value, Value):
                other_configuration[key] = value

            elif isinstance(value, self.__class__):
                #another tree
                other_value = other_configuration._getRaw(key)
                if isinstance(other_value, self.__class__):
                    #recurse overriding the other tree
                    value.override(other_value, propagate_deleted_keys=propagate_deleted_keys)
                else:
                    #just erase the other value
                    assert isinstance(other_value, Value)
                    other_configuration[key] = self[key]

    def toDict(self):
        result = {}
        for key, value in self.iteritems():
            if isinstance(value, self.__class__):
                value = value.toDict()
            elif isinstance(value, Value):
                value = value.value
            result[key] = value
        return result

    def iterleafs(self):
        chain = []
        for key, value in self.iteritems():
            if isinstance(value, self.__class__):
                chain.append(value)
            elif isinstance(value, Value):
                yield value.value
            else:
                yield value
        for item in chain:
            for leaf in item.iterleafs():
                yield leaf

    def mkXMLTree(self):
        root = ET.Element(CONFIG_ROOT_TAG)
        root.set(VERSION_ATTR, VERSION)

        names = self.keys()
        names.sort()
        for name in names:
            storage = dict.__getitem__(self, name)
            self._exportXMLValue(root, name, storage)
        self._saveDeletedKeys(root)
        return root

    def _saveDeletedKeys(self, parent):
        for item in self.deleted_keys:
            sub_block = ET.SubElement(parent, DELETED_KEY_TAG)
            sub_block.text = escape(unicode(item))

    def save(self, filename):
        root = self.mkXMLTree()
        return self._save(root, filename)

    def _save(self, root, filename):
        umask(0077)
        try:
            return xml_save(root, filename)
        except IOError, err:
            raise ConfigError(CONFIG_ERR_XML_WRITE,
                tr('Unable to write into %s XML file: %s'),
                filename, exceptionAsUnicode(err))

    def printMe(self, indent = 0):
        prepend = " " * indent
        text = "\n%s\\\n" % prepend
        for key, value in self.iteritems():
            text += "%s| %s\n" % (prepend, key)
            descr = value.printMe(indent + 2) if isinstance(value, self.__class__) else value
            text += "%s > [%s] %s\n" % (prepend, type(value), descr)
        if indent == 0:
            print text
            print repr(self)
        return text

    def _exportXMLValue(self, parent, name, value):
        if isinstance(value, self.__class__):
            value._saveUnderParent(parent, name)
        elif isinstance(value, Value):
            sub_block = ET.SubElement(parent, DATA_TAG)
            sub_block.set(NAME_ATTR, escape(name))
            if not value.type in ('str', 'unicode'):
                sub_block.set(TYPE_ATTR, escape(value.type))
            sub_block.text = escape(unicode(value.string))
        else:
            raise NotImplementedError("Cannot serialize to XML: type %s." % type(value))

    def _saveUnderParent(self, parent_node, name):
        block = ET.SubElement(parent_node, CONFIG_ELT_TAG)
        block.set(NAME_ATTR, escape(name))

        names = self.keys()
        names.sort()
        for sub_elt_name in names:
            sub_elt = dict.__getitem__(self, sub_elt_name)
            self._exportXMLValue(block, sub_elt_name, sub_elt)
        self._saveDeletedKeys(block)

    def load(self, filename):
        """
        Loads an xml file and fills this VariablesStore object with it.
        """
        try:
            with open(filename) as fp:
                tree = ET.parse(fp)
            root = tree.getroot()
        except IOError, err:
            raise ConfigError(CONFIG_NO_SUCH_FILE,
                tr('Unable to open %s XML file: %s!'),
                filename, exceptionAsUnicode(err))
        except Exception:
            #Not sure of exception type, likely ExpatError
            raise ConfigError(
                CONFIG_ERR_XML_READ,
                'Invalid XML in file %s' % filename
                )
        self.checkXMLroot(root)
        self.clear()
        self._populateFromEtree(root)

    def checkXMLroot(self, root):
        if root.tag != CONFIG_ROOT_TAG:
            raise ConfigError(CONFIG_ERR_XML_READ,
                tr('XML root is not %s'), CONFIG_ROOT_TAG)
        for item in root.items():
            if item[0] == VERSION_ATTR:
                if item[1] == VERSION:
                    return
                else:
                    raise ConfigError(CONFIG_ERR_XML_READ,
                        tr('VariablesStore version expected: %s, got %s'),
                        VERSION, item[1])
        raise ConfigError(CONFIG_ERR_XML_READ,
            tr('VariablesStore version not found (expected version="%s")'),
            VERSION)

    def _populateFromEtree(self, parent):
        for child in parent.getchildren():
            _type = None
            key = _type = None
            for item in child.items():
                if item[0] == NAME_ATTR:
                    key = unescape(item[1])
                if item[0] == TYPE_ATTR:
                    _type = unescape(item[1])

            self.parseTag(child, key, _type)

    def parseTag(self, child, key, _type):
        if child.tag == CONFIG_ELT_TAG:
            conf = self.__class__()
            self[key] = conf
            conf._populateFromEtree(child)
        if child.tag == DATA_TAG:
            text = child.text
            if text:
                text = unescape(child.text)
            else:
                text = u''
            if _type is None:
                value = Value(text)
            else:
                value = Value.fromType(_type, text)
            self[key] = value
        elif child.tag == DELETED_KEY_TAG:
            text = child.text
            text = unescape(child.text)
            self.deleted_keys.add(text)

    def getValue(self, path):
        if len(path) == 0:
            return self
        local_part = path[0]

        value = self[local_part]

        if len(path) == 1:
            return value
        else:
            try:
                result = value.getValue(path[1:])
                return result
            except TypeError:
                raise ConfigError(CONFIG_PATH_TOO_LONG,
                    tr("Path too long, can not recurse past tree leafs (values)"))
            except KeyError, err:
                if local_part in self.deleted_keys:
                    raise ConfigError(CONFIG_VALUE_DELETED, "Value deleted")
                raise err

    def isPathDeleted(self, path):
        if len(path) == 0:
            return False
        local_part = path[0]
        return local_part in self.deleted_keys

