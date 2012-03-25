
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
from PyQt4.QtGui import QFileDialog
from ufwi_rpcd.common import tr
from ufwi_rpcd.common.service_status_values import ServiceStatusValues
from .cell_data import CellData
from .cell_edw import GlobalStatus, AttributeCheckBox, FileDialogButton
from .cell_widget import EdwCell
from .strings import APP_TITLE

class GenericGlobalStatus(GlobalStatus):
    def __init__(self, edw_list, perms):
        CellData.__init__(self, perms)
        self.edw_list = edw_list

    def getWidget(self):
        icon = 'online'
        if self.getStatusCount('online') != len(self.edw_list):
            icon = 'offline'
        return EdwCell(self.getText(), self.getIcon(icon))

    def getStatusCount(self, status):
        count = 0
        for edw in self.edw_list:
            if edw.global_status == status:
                count += 1
        return count

    def getText(self):
        count = self.getStatusCount('online')
        if count != len(self.edw_list):
            return '%i offline' % (len(self.edw_list) - count)
        else:
            return '%i online' % count

    def getValue(self):
        return u''
    def getTooltip(self):
        text = tr('<b>%i firewalls:</b>') % len(self.edw_list)
        for status in ('error', 'offline', 'registering', 'online'):
            count = self.getStatusCount(status)
            if count != 0:
                if text != '':
                    text += '<br>'
                text += tr('%i %s') % (count, status)
        return text

class GenericServiceStatus(CellData):
    STATUS_TO_ICON = {
        ServiceStatusValues.STOPPED: ':/icons-20/off_line.png',
        ServiceStatusValues.NOT_LOADED: ':/icons-20/not_available.png',
        ServiceStatusValues.POLLING: ':/icons-20/refresh.png',
        ServiceStatusValues.RUNNING: ':/icons-20/on_line.png',
    }

    def __init__(self, edw_list, perms, svc):
        CellData.__init__(self, perms)
        self.edw_list = edw_list
        self.svc = svc

    def getTooltip(self):
        status = tr('Service <b>%s</b>:') % self.svc
        if self.getStatusCount(ServiceStatusValues.RUNNING):
            status += tr('<br>- running on %i firewalls' % self.getStatusCount(ServiceStatusValues.RUNNING))
        if self.getStatusCount(ServiceStatusValues.STOPPED):
            status += tr('<br>- stopped on %i firewalls' % self.getStatusCount(ServiceStatusValues.STOPPED))
        if self.getStatusCount(ServiceStatusValues.NOT_LOADED):
            status += tr('<br>- not loaded on %i firewalls' % self.getStatusCount(ServiceStatusValues.NOT_LOADED))
        return status

    def getStatusCount(self, status):
        count = 0
        for edw in self.edw_list:
            if self.svc in edw.getServices().keys() and edw.getServices()[self.svc] == status:
                count += 1
        return count

    def getIcon(self):
        count = self.getStatusCount(ServiceStatusValues.RUNNING)
        if count == len(self.edw_list):
            return self.STATUS_TO_ICON[ServiceStatusValues.RUNNING]
        return self.STATUS_TO_ICON[ServiceStatusValues.STOPPED]

    def getValue(self):
        return u''

    def getWidget(self):
        count = self.getStatusCount(ServiceStatusValues.RUNNING)
        if count == len(self.edw_list):
            txt = str(len(self.edw_list))
        else:
            txt = str(len(self.edw_list) - count)
        return EdwCell(txt, self.getIcon())

class GenericSumAttributeCell(CellData):
    def __init__(self, edw_list, perms, attr):
        CellData.__init__(self, perms)
        self.edw_list = edw_list
        self.attr = attr

    def getWidget(self):
        sum = 0
        for edw in self.edw_list:
            attr = getattr(edw, self.attr)
            if isinstance(attr, int):
                sum += attr
        return EdwCell(tr('Total: %i' % sum))

class GenericCheckBox(AttributeCheckBox):
    def __init__(self, edw, edw_list, perms, attr):
        AttributeCheckBox.__init__(self, edw, perms, attr)
        self.edw_list = edw_list

    def getValue(self):
        return u''

    def setCheckbox(self, val):
        setattr(self.edw, self.attr, val)
        for edw in self.edw_list:
            setattr(edw, self.attr, val)
            edw.emit(SIGNAL('display_cell'), edw, self.attr)
        self.edw.emit(SIGNAL('display_cell'), self.edw, self.attr)

class GenericFileDialogButton(FileDialogButton):
    def __init__(self, edw, edw_list, perms, attr):
        FileDialogButton.__init__(self, edw, perms, attr)
        self.edw_list = edw_list

    def setFilePath(self):
        dlg = QFileDialog(None, APP_TITLE)
        if dlg.exec_():
            val = dlg.selectedFiles()[0]
            #val = [unicode(i) for i in val]
            #val = val[0]

            if self.edw.askConfirmation(tr("This will assign the file to %i firewalls.\nAre you sure you want to do this?") % self.edw.countRole(self.perms)):
                for edw in self.edw_list:
                    setattr(edw, self.attr, str(val))
                    edw.emit(SIGNAL('display_cell'), edw, self.attr)
    def getValue(self):
        return u''

