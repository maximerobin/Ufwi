
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

from PyQt4.QtCore import QObject
from ufwi_rpcd.common import tr
from time import time
from .cell_widget import EdwBlankCell, EdwCell

class EdwData(QObject):
    ATTR_GETTER = {
    }

    def __init__(self, window, client, id):
        QObject.__init__(self)
        self.id = id
        self.window = window
        self.client = client
        self.roles = set()

    def haveRole(self, role):
        if self.window.is_admin:
            return True
        if role[-6:] == '_write' and self.window.read_only:
            return False
        return role in self.getEdwObj().roles

    def haveRoles(self, roles):
        if self.window.is_admin:
            return True
        for role in roles:
            if not self.getEdwObj().haveRole(role):
                return False
        return True

    def getID(self):
        return self.id

    def getEdwName(self):
        return self.name

    def getEdwObj(self):
        if self.isHeader():
            return None
        for edw in self.window.edw_list:
            if edw.getID() == self.getEdwName():
                return edw
        return None

    def getCell(self, attr):
        if attr in self.cell_classes:
            if isinstance(self.cell_classes[attr].perms, list):
                perms = self.cell_classes[attr].perms
            elif hasattr(self, self.cell_classes[attr].perms) and callable(getattr(self, self.cell_classes[attr].perms)):
                get_perm_func = getattr(self, self.cell_classes[attr].perms)
                perms = get_perm_func()
            else:
                raise Exception('Unhandled permission type')

            if not self.haveRoles(perms):
                return tr('Permission denied'), EdwCell(tr('Permission denied'), ':/icons-20/off_line.png')
            return self.cell_classes[attr].getValue(), self.cell_classes[attr].getCell()

        if attr[:8] == "category":
            if self.isHeader():
                return self.getCategoryCell(attr)
            if self.getEdwObj():
                return self.getEdwObj().getCategoryCell(attr)

        return u'', EdwBlankCell()

    def getVal(self, attr):
        if attr in self.cell_classes:
            return self.cell_classes[attr].getValue()

        if attr[:8] == "category":
            if self.isHeader():
                return self.getCategoryCell(attr)
            if self.getEdwObj():
                return self.getEdwObj().getCategoryVal(attr)

        return u''

    def getDeltaDateStr(self, val):
        txt = ''
        if val == 0:
            txt = tr('Unknown')
        else:
            val = int(time()) - int(val)
            txt = ''
            if val == 0:
                txt = tr('never')
            elif val < 10:
                txt = tr('less than 10 seconds ago')
            elif val < 60:
                txt = tr('%i second(s) ago') % val
            elif val < 60 * 60:
                txt = tr('%i:%02i minute(s) ago') % (val / 60, val % 60)
            elif val < 60 * 60 * 24:
                txt = tr('%i:%02i hour(s) ago') % (val / (60 * 60), (val / 60) % 60)
            elif val < 60 * 60 * 24 * 30.5:
                txt = tr('%i day(s)') % (val / (60 * 60 * 24))
            elif val < 60 * 60 * 24 * 356:
                txt = tr('%i month(s)') % (val / (60 * 60 * 24 * 30.5))
            else:
                txt = tr('%i year(s)') % (val / (60 * 60 * 24 * 365))
        return txt
