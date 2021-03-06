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

class StoredObject:

    sections = {}

    def __init__(self, name):
        self.name = name
        self.default = False

    def isDefault(self):
        return self.default

    def setDefault(self, b):
        self.default = b

    def load(self, items):
        raise NotImplementedError()

    def properties(self):
        raise NotImplementedError()
