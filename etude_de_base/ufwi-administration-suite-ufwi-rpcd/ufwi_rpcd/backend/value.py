# -*- coding: utf-8 -*-

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


class Value(object):

    def __init__(self, value):
        self.type = type(value).__name__
        self.value = value

        try:
            method = getattr(Value, 'type_set_%s' % self.type)
        except AttributeError:
            raise TypeError("Invalid value type: %s" % type(value))

        self.string = method(value)

    @staticmethod
    def fromType(_type, string):
        """
        Create a Value object from a type and an unicode value.
        @param _type  type wanted (str)
        @param string  value's string (unicode)
        @return  Value object
        """
        try:
            method = getattr(Value, 'type_get_%s' % _type)
        except AttributeError:
            raise TypeError("Invalid value type: %s" % _type)

        return Value(method(string))

    def __repr__(self):
        return "<Value object '%s'>" % self.value

    @staticmethod
    def type_set_bool(value): return unicode(int(value))
    @staticmethod
    def type_get_bool(value): return bool(int(value))

    @staticmethod
    def type_set_NoneType(value): return unicode('')
    @staticmethod
    def type_get_NoneType(value): return None

    @staticmethod
    def type_set_unicode(value): return unicode(value)
    @staticmethod
    def type_get_unicode(value): return unicode(value)

    @staticmethod
    def type_set_int(value): return unicode(value)
    @staticmethod
    def type_get_int(value): return int(value)

    @staticmethod
    def type_set_long(value): return unicode(value)
    @staticmethod
    def type_get_long(value): return long(value)

    @staticmethod
    def type_set_str(value): return unicode(value)
    @staticmethod
    def type_get_str(value): return str(value)

    @staticmethod
    def type_set_float(value): return unicode(value)
    @staticmethod
    def type_get_float(value): return float(value)

