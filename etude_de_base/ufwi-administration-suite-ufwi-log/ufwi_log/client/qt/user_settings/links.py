# -*- coding: utf-8 -*-

"""
Copyright (C) 2008-2011 EdenWall Technologies
Written by Romain Bignon <romain AT inl.fr>

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

from ufwi_log.client.qt.user_settings.stored import StoredObject
from ufwi_log.client.qt.args import arg_types

class Links(StoredObject):

    def isDefault(self): return False
    def setDefault(self, b): pass

    def __repr__(self):
        return "<Links>"

    def load(self, items):
        for key, value in items.items():
            try:
                arg_types[key].pagelinks = value.split(' ')
            except KeyError:
                pass

    def properties(self):
        props = {}
        for key, value in arg_types.items():
            if value.pagelinks:
                props[key] = ' '.join(value.pagelinks)

        return props


