
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

from PyQt4.QtCore import SIGNAL, QSize
from PyQt4.QtGui import QColor, QFileDialog
from ufwi_rpcd.common import tr
from ufwi_rpcd.common.service_status_values import ServiceStatusValues
from .cell_data import CellData, COLOR_RED, COLOR_GREEN
from .cell_widget import EdwCell, EdwBlankCell, EdwProgressBarCell, EdwCheckBoxCell, EdwButtonCell
from .strings import APP_TITLE

class GlobalStatus(CellData):
    STATUS_TO_ICON = {
        'online': ':/icons-20/on_line.png',
        'registering': ':/icons-20/run.png',
    }
    DEFAULT_ICON = ':/icons-20/off_line.png'

    def __init__(self, edw, perms):
        CellData.__init__(self, perms)
        self.edw = edw

    def getIcon(self, status):
        if status in self.STATUS_TO_ICON.keys():
            icon = self.STATUS_TO_ICON[status]
        else:
            icon = self.DEFAULT_ICON
        return icon

    def getValue(self):
        return self.edw.global_status

    def getWidget(self):
        return EdwCell(self.getValue(), self.getIcon(self.getValue()))

class ServiceStatus(CellData):
    STATUS_TO_ICON = {
        ServiceStatusValues.STOPPED: ':/icons-20/off_line.png',
        ServiceStatusValues.NOT_LOADED: ':/icons-20/not_available.png',
        ServiceStatusValues.POLLING: ':/icons-20/refresh.png',
    }
    DEFAULT_ICON = ':/icons-20/on_line.png'

    def __init__(self, edw, perms, svc):
        CellData.__init__(self, perms)
        self.edw = edw
        self.svc = svc

    def getTooltip(self):
        if self.edw.global_status == 'online':
            status = self.getValue()
            if status == ServiceStatusValues.RUNNING:
                status = tr('Service <b>%s</b> is running') % self.svc
            elif status == ServiceStatusValues.STOPPED:
                status = tr('Service <b>%s</b> is stopped') % self.svc
            elif status == ServiceStatusValues.NOT_LOADED:
                status = tr('Service <b>%s</b> is not loaded') % self.svc
            return status
        return None

    def getIcon(self, status):
        if self.edw.global_status == 'online':
            if status in self.STATUS_TO_ICON.keys():
                icon = self.STATUS_TO_ICON[status]
            else:
                icon = self.DEFAULT_ICON
            return icon
        return None

    def getValue(self):
        return self.edw.services_status[self.svc]

    def getWidget(self):
        if self.getValue() == ServiceStatusValues.RUNNING:
            self.setColor(COLOR_GREEN)
        elif self.getValue() == ServiceStatusValues.STOPPED:
            self.setColor(COLOR_RED)
        else:
            self.setColor(None)
        if self.getIcon(self.getValue()):
            return EdwCell(u'', self.getIcon(self.getValue()))
        return EdwBlankCell()

class AttributeProgressBar(CellData):
    def __init__(self, edw, perms, attr, attr_min, attr_max, col_min, col_max, format = '%v'):
        CellData.__init__(self, perms)
        self.edw = edw
        self.attr = attr
        self.attr_max = attr_max
        self.attr_min = attr_min
        self.col_min = col_min
        self.col_max = col_max
        self.format = format

    def setFormat(self, format):
        self.format = format

    def getWidget(self):
        val = getattr(self.edw, self.attr)
        max = getattr(self.edw, self.attr_max)
        min = getattr(self.edw, self.attr_min)
        if isinstance(val, int) and isinstance(max, int) and isinstance(min, int) and min >= 0:
            col_min = QColor(self.col_min)
            col_max = QColor(self.col_max)

            if min != max:
                r_min, g_min, b_min, a_min = col_min.getRgb()
                r_max, g_max, b_max, a_max = col_max.getRgb()
                c_r = ((val - min) * (r_max - r_min) / (max - min)) + r_min
                c_g = ((val - min) * (g_max - g_min) / (max - min)) + g_min
                c_b = ((val - min) * (b_max - b_min) / (max - min)) + b_min

                # If the min / max values has not yet been refreshed, then we could get weird colors
                if c_r < 0: c_r = 0
                if c_g < 0: c_g = 0
                if c_b < 0: c_b = 0
                if c_r > 255: c_r = 255
                if c_g > 255: c_g = 255
                if c_b > 255: c_b = 255

                color = "#%02x%02x%02x" % (c_r, c_g, c_b)
            else:
                color = col_min

            return EdwProgressBarCell(val, max, color, self.format)
        return EdwBlankCell()

    def getValue(self):
        val = getattr(self.edw, self.attr)
        max = getattr(self.edw, self.attr_max)
        if isinstance(val, int) and isinstance(max, int):
            return val
        return 0

class AttributeCheckBox(CellData):
    def __init__(self, edw, perms, attr):
        CellData.__init__(self, perms)
        self.edw = edw
        self.attr = attr

    def getWidget(self):
        widget = EdwCheckBoxCell(getattr(self.edw, self.attr), self.setCheckbox)
        return widget

    def getValue(self):
        return unicode(getattr(self.edw, self.attr))

    def setCheckbox(self, val):
        setattr(self.edw, self.attr, val)
        self.edw.emit(SIGNAL('display_cell'), self.edw, self.attr)

class FileDialogButton(CellData):
    def __init__(self, edw, perms, attr):
        CellData.__init__(self, perms)
        self.edw = edw
        self.attr = attr

    def getWidget(self):
        cell = EdwButtonCell('...', self.setFilePath)
        cell.setMaximumSize(QSize(30, 30))
        return cell

    def setFilePath(self):
        dlg = QFileDialog(None, APP_TITLE)
        if dlg.exec_():
            val = dlg.selectedFiles()[0]
            #val = [unicode(i) for i in val]
            #val = val[0]
            setattr(self.edw, self.attr, str(val))
            self.edw.emit(SIGNAL('display_cell'), self.edw, self.attr)
    def getValue(self):
        return getattr(self.edw, self.attr)

