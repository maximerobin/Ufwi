# -*- coding: utf-8 -*-
"""
Copyright (C) 2007-2011 EdenWall Technologies
Written by Victor Stinner <victor.stinner AT inl.fr>

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

$Id$
"""

import re
from datetime import datetime
from ufwi_rpcd.common.human import typeName
from ufwi_rpcd.common.timezone import parseTimezone

_DATETIME_REGEX = re.compile(
    ur"^(?P<year>[0-9]{4})-(?P<month>[0-9]{2})-(?P<day>[0-9]{2}) "
    ur"(?P<hour>[0-9]{2}):(?P<minute>[0-9]{2}):(?P<second>[0-9]{2})"
    ur"(?P<end>.*)$")

_MICROSECOND_REGEX = re.compile(ur"^\.([0-9]{6})(.*)$")

class TransportError(Exception):
    pass

MAX_INT =  2L**31-1
MIN_INT = -2L**31

# Type allowed in XML-RPC
# List of simple type are also allowed
SIMPLE_TYPES = (bool, float)

# Allowed byte/character in strings (match only one byte/character)
BYTES_REGEX = re.compile("^[\t\r\n\x20-\x7e]$")
UNICODE_REGEX = re.compile(u'^[\t\r\n\x20-\uffff]$')

def checkString(value):
    if isinstance(value, str):
        for byte in value:
            if not BYTES_REGEX.match(byte):
                raise TransportError("Invalid byte in string %r" % byte)
        return True
    elif isinstance(value, unicode):
        for char in value:
            if not UNICODE_REGEX.match(char):
                raise TransportError("Invalid unicode character in string %r" % char)
        return True
    else:
        return False

def checkSimpleType(value):
    if checkString(value):
        return True
    elif isinstance(value, SIMPLE_TYPES):
        return True
    elif isinstance(value, (int, long)):
        if not (MIN_INT <= value <= MAX_INT):
            raise TransportError("long int (%s) exceeds XML-RPC limits" % value)
        return True
    else:
        raise TransportError("Unserializable type: %s" % typeName(value))

def checkComplexType(result):
    result_type = type(result)
    if result_type in (tuple, list):
        for item in result:
            checkComplexType(item)
    elif result_type is dict:
        for key, value in result.iteritems():
            if not checkString(key):
                raise TransportError("A dictionary key have to be a string, not a %s" % typeName(key))
            checkComplexType(value)
    else:
        checkSimpleType(result)

def parseDatetime(text):
    """
    >>> parseDatetime('2008-11-24 15:28:01')
    datetime.datetime(2008, 11, 24, 15, 28, 1)
    >>> parseDatetime('2008-11-24 15:28:01.359668')
    datetime.datetime(2008, 11, 24, 15, 28, 1, 359668)
    >>> parseDatetime('2008-11-24 15:28:01 UTC')
    datetime.datetime(2008, 11, 24, 15, 28, 1, tzinfo=<UTC>)
    >>> parseDatetime('2008-11-24 15:28:01+00:00')
    datetime.datetime(2008, 11, 24, 15, 28, 1, tzinfo=<UTC>)
    >>> parseDatetime('2008-11-24 15:28:01.359668 UTC')
    datetime.datetime(2008, 11, 24, 15, 28, 1, 359668, tzinfo=<UTC>)
    >>> parseDatetime('2008-11-24 15:28:01.359668+00:00')
    datetime.datetime(2008, 11, 24, 15, 28, 1, 359668, tzinfo=<UTC>)
    """
    # Note: Python 2.6 supports "%f" for the microseconds, so it's just:
    #    return datetime.strptime(text, '%Y-%m-%d %H:%M:%S.%f')
    text = unicode(text)
    match = _DATETIME_REGEX.match(text)
    if not match:
        raise TransportError("Invalid timestamp: %r" % text)
    data = match.groupdict()
    year = int(data['year'])
    month = int(data['month'])
    day = int(data['day'])
    hour = int(data['hour'])
    minute = int(data['minute'])
    second = int(data['second'])
    microsecond = 0
    end = data['end']
    if end:
        match = _MICROSECOND_REGEX.match(end)
        if match:
            microsecond = int(match.group(1))
            end = match.group(2)
    end = end.lstrip(' ')
    if end:
        tzinfo = parseTimezone(end)
    else:
        tzinfo = None
    return datetime(
        year, month, day, hour,
        minute, second, microsecond,
        tzinfo=tzinfo)
