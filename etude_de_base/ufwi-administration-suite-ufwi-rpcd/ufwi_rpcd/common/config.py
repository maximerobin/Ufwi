#coding: utf-8
"""
$Id :$
A facility to store iterables in dictionnaries and restore them afterwards.
Indexes are strings to be allowed in XML-RPC.


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


from IPy import IP
from ufwi_rpcd.common.human import humanRepr

UNSET = "___UNSET___"

_TYPES_MAPPING = {}

def register_type(path, name=None):
    _TYPES_MAPPING[path] = path
    if name is not None:
        #double mapping: by name and path
        _TYPES_MAPPING[name] = path

#support old names
for name in (
    'ufwi_rpcd.common.radius_client.RadiusServer',
    'ufwi_rpcd.common.radius_client.RadiusConf',
    ):
    register_type(name)

def list2dict(iterable):
    return dict(
        ((unicode(index), value) for index, value in enumerate(iterable))
    )

def dict2list(dictionnary):
    """
    Works for dictionnaries generated with list2dict
    Returns a list, ordered if it was ordered
    """
    if dictionnary is None:
        return ()
    result = [None for x in xrange(len(dictionnary))]
    for num_key, value in dictionnary.iteritems():
        result[int(num_key)] = value
    return result

class UnserializableElement(Exception):
    pass

def serializeElement(value, extensions=()):
    """
    extensions is an iterable of duples, this way:
    (
        (type, method_name),
        (type, method),
        ...
    )
    If a method is supplied, it will receive value.
    If a method_name is supplied, the method value.method_name will be used
    Note: an ordered iterable is a good idea.

    """

    if extensions:
        for _type, _serializer in extensions:
            if isinstance(value, _type):
                if isinstance(_serializer, (str, unicode)):
                    _serializer = getattr(value, _serializer)
                    return _serializer()
                return _serializer(value)

    if isinstance(value, dict):
        value = value.copy()
        value['__type__'] = 'dict'
        for key, val in value.iteritems():
            value[key] = serializeElement(val, extensions=extensions)
    elif isinstance(value, (list, tuple)):
        if isinstance(value, list):
            type_name = 'list'
        else:
            type_name = 'tuple'
        value = list2dict(value)
        value['__type__'] = type_name
        for key, val in value.iteritems():
            value[key] = serializeElement(val, extensions=extensions)
    elif isinstance(value, set):
        value = list2dict(value)
        value['__type__'] = 'set'
        for key, val in value.iteritems():
            value[key] = serializeElement(val, extensions=extensions)
    elif isinstance(value, IP):
        element = unicode(value)
        value = {}
        value['__type__'] = 'IP'
        value['IP'] = element
    elif value is None:
        value = UNSET

    elif not isinstance(value, (str, int, long, bool, float, unicode)):
        raise UnserializableElement("Unserialisable value: %s" % humanRepr(value))

    return value

def deserializeElement(serialized):

    if isinstance(serialized, dict) and '__type__' in serialized:
        obj_type = serialized['__type__']
        if obj_type in ('list', 'tuple'):
            deserialized = serialized.copy()
            del deserialized['__type__']
            deserialized = dict2list(deserialized)
            for i, val in enumerate(deserialized):
                deserialized[i] = deserializeElement(val)
            if obj_type == 'tuple':
                deserialized = tuple(deserialized)
            return deserialized
        elif 'set' == obj_type:
            deserialized = serialized.copy()
            del deserialized['__type__']
            return set(
                deserializeElement(item) for item in dict2list(deserialized)
                )
        elif 'dict' == obj_type:
            deserialized = serialized.copy()
            del deserialized['__type__']
            for key, val in deserialized.iteritems():
                deserialized[key] = deserializeElement(val)
            return deserialized
        elif 'IP' == obj_type:
            return IP(serialized['IP'])
        else:
            deserialized = serialized.copy()
            if obj_type not in _TYPES_MAPPING:
                raise UnserializableElement("Unhandled type %s" % obj_type)
            names = obj_type.rsplit('.', 1)
            _module = __import__(names[0], globals(), locals(), [names[1]], -1)

            _class = getattr(_module, names[1], None)
            if _class is None:
                raise UnserializableElement("Cannot find class %s" % obj_type)
            _deserializer = getattr(_class, 'deserialize', None)
            if _deserializer is None:
                raise UnserializableElement("Class %s has no 'deserialize' method" % obj_type)
            return _deserializer(serialized)
        raise UnserializableElement(serialized)
    elif UNSET == serialized:
        return None

    # probably a primitive type
    return serialized
