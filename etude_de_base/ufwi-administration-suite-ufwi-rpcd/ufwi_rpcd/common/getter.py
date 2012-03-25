
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

def getOptional(getter, data, default=None):
    """
    Return:
     - default if data is None or an empty list, tuple, string, ...
     - or getter(data) otherwise (if data is set).
    """
    if (not data) and (not isinstance(data, (int, long))):
        # empty string, list, tuple, None, ..., but not 0 or 0L
        return default
    return getter(data)

def getOptionalDict(getter, data, key, default=None):
    """
    Get the optional value from data. Return:
     - getter(data[key]) and remove the value if the key exists
     - or default if the key doesn't exist
    """
    if key in data:
        return getter(data.pop(key))
    else:
        return default

def getBoolean(data):
    return bool(data)

def getInteger(data):
    return int(data)

def getUnicode(data):
    return unicode(data).strip()

def getList(getter, data):
    if not isinstance(data, (list, tuple)):
        raise TypeError("Expected a tuple or a list, got a %s" % typeName(data))
    return [getter(item) for item in data]

def getTuple(getter, data):
    return tuple(getter(item) for item in data)

def getDict(key_getter, value_getter, data):
    return dict(
        (key_getter(key), value_getter(value))
        for key, value in data.iteritems())

