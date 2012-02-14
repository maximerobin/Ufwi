#coding: utf-8
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

from PyQt4.QtCore import QSize
from PyQt4.QtGui import QPushButton, QIcon

from ufwi_rpcd.common import tr

class Button(QPushButton):
    _ICON_SIZE = 16
    def __init__(self, text=None, flat=True, parent=None, enabled=True):
        QPushButton.__init__(self, parent)
        self.setEnabled(enabled)
        self.setFlat(flat)
        if text is not None:
            self.setText(text)
        self.setIconSize(QSize(Button._ICON_SIZE, Button._ICON_SIZE))

    def setText(self, text):
        QPushButton.setText(self, text)
        self.fixWidth(text)

    def fixWidth(self, text):
        chars = len(text) + 6 # safe margin
        textwidth = self.fontMetrics().averageCharWidth() * chars
        outermargin = 20
        wanted_with = Button._ICON_SIZE + outermargin + textwidth
        self.setFixedWidth(wanted_with)

class AddButton(Button):
    def __init__(self, text=tr("New"), parent=None):
        Button.__init__(self, text=text, parent=parent, flat=False)
        self.setIcon(QIcon(":/icons/add.png"))
        self.setToolTip(tr("Click to add an item"))

class RemButton(Button):
    def __init__(self, text=tr("Delete"), parent=None):
        Button.__init__(self, text=text, parent=parent, flat=False)
        self.setIcon(QIcon(":/icons/delete.png"))
        self.setToolTip(tr("Click to delete selected item"))

class UpButton(Button):
    def __init__(self, parent=None):
        Button.__init__(self, parent=parent, flat=False)
        self.setIcon(QIcon(":/icons/up.png"))

class DownButton(Button):
    def __init__(self, parent=None):
        Button.__init__(self, parent=parent, flat=False)
        self.setIcon(QIcon(":/icons/down.png"))

