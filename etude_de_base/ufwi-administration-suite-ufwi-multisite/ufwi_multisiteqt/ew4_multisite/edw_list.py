
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

from PyQt4.QtCore import SIGNAL
from ufwi_rpcd.common import tr
from .obj_list import ObjList
from .edw_generic import GenericEdw

class EdwList(ObjList):
    def __init__(self, client, table, ui, obj_list, group):
        self.edw_generic = GenericEdw(table, obj_list, client)
        self.connect(self.edw_generic, SIGNAL('display_cell'), self.displayCell)
        ObjList.__init__(self, client, table, ui, obj_list, group)

    def newObj(self, edw):
        ObjList.newObj(self, edw)
        self.edw_generic.connect(edw, SIGNAL('refresh_min_max'), self.edw_generic.refreshAttrMinMax)


    def getHeader(self):
        return self.edw_generic

    @staticmethod
    def getObjectTypeName():
        return tr('firewall')
