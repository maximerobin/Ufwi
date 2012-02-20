# -*- coding: utf-8 -*-

"""
Copyright (C) 2010-2011 EdenWall Technologies

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

class EmptyDB(object):
    def __init__(self, *args, **kw):
        self.database = None

    def rehash(self, *args, **kw):
        pass

class Exporter(EmptyDB):
    pass

class Importer(EmptyDB):
    pass

class squid(object):
    class Squid(EmptyDB):
        pass

