
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

from PyQt4.QtCore import Qt
from PyQt4.QtGui import QColor, QPalette
from .cell_widget import EdwCell, EdwBlankCell, EdwComboBoxCell

COLOR_RED = "#FF9D9F"
COLOR_GREEN = "#B0FF86"

class CellData():
    def __init__(self, perms = [], font = None, color = None):
        self.font = font
        self.color = color
        self.perms = perms
        self.actions = []

    def getWidget(self):
        raise "Not implemented"

    def getCell(self):
        widget = self.getWidget()
        if not self.getTooltip() is None:
            widget.setToolTip(self.getTooltip())
        if not self.font is None:
            widget.setFont(self.font)
        if not self.getColor() is None:
            pal = widget.palette()
            pal.setColor(QPalette.Base, QColor(self.getColor()))
            widget.setPalette(pal)
        if len(self.actions):
            for action in self.actions:
                widget.addAction(action)
            widget.setContextMenuPolicy(Qt.ActionsContextMenu)
        return widget

    def getValue(self):
        return 0

    def getTooltip(self):
        try:
            tooltip = getattr(self.edw, self.attr + '_tooltip')
            return tooltip
        except AttributeError:
            return None

    def setFont(self, font):
        self.font = font

    def setColor(self, color):
        self.color = color

    def getColor(self):
        return self.color

    def setActions(self, actions):
        self.actions = actions

class AttributeCell(CellData):
    def __init__(self, edw, perms, attr):
        CellData.__init__(self, perms)
        self.edw = edw
        self.attr = attr

    def getWidget(self):
        return EdwCell(self.getValue())

    def getValue(self):
        return getattr(self.edw, self.attr)

class AttributeDate(AttributeCell):
    def __init__(self, edw, perms, attr):
        AttributeCell.__init__(self, edw, perms, attr)

    def getWidget(self):
        from datetime import datetime
        d = datetime.fromtimestamp(self.getValue())
        return EdwCell(d)

class AttributeTime(AttributeCell):
    def __init__(self, edw, perms, attr):
        AttributeCell.__init__(self, edw, perms, attr)

    def getWidget(self):
        from datetime import datetime
        d = datetime.fromtimestamp(self.getValue())
        d -= datetime.fromtimestamp(0)

        return EdwCell(str(d))

class AttributeImg(AttributeCell):
    def __init__(self, edw, perms, attr, icon_attr):
        AttributeCell.__init__(self, edw, perms, attr)
        self.icon_attr = icon_attr

    def getWidget(self):
        return EdwCell(self.getValue(), getattr(self.edw, self.icon_attr))

class AttributeFile(AttributeCell):
    def getValue(self):
        from os.path import split
        return split(getattr(self.edw, self.attr))[1]

class BlankCell(CellData):
    def __init__(self, perms = []):
        CellData.__init__(self, perms)

    def getWidget(self):
        return EdwBlankCell()

class AttributeBool(AttributeCell):
    ICONS = { True : ':/icons-20/on_line.png', False : ':/icons-20/off_line.png' }
    def __init__(self, edw, perms, attr, attr_bool):
        CellData.__init__(self, perms)
        self.edw = edw
        self.attr = attr
        self.attr_bool = attr_bool

    def getValue(self):
        return getattr(self.edw, self.attr_bool)

    def getWidget(self):
        return EdwCell(getattr(self.edw, self.attr), self.ICONS[getattr(self.edw, self.attr_bool)])

class AttributeComboBox(CellData):
    def __init__(self, edw, perms, combo_list, combo_val, callback):
        CellData.__init__(self, perms)
        self.edw = edw
        self.combo_list = combo_list
        self.combo_val = combo_val
        self.callback = callback

    def getValue(self):
        return getattr(self.edw, self.combo_val)

    def getWidget(self):
        combo_list = getattr(self.edw, self.combo_list)
        combo_val = getattr(self.edw, self.combo_val)
        return EdwComboBoxCell(combo_list, combo_val, self.callback)

