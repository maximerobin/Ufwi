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

from PyQt4.QtCore import Qt, SIGNAL
from PyQt4.QtGui import (QWidget, QFrame, QHBoxLayout, QLabel, QCheckBox,
    QGroupBox, QFormLayout)

from ufwi_conf.client.qt.scrollarea import ScrollArea
from ufwi_conf.client.qt.full_featured_scrollarea import FullFeaturedScrollArea

class IpDisplayList(QLabel):
    def __init__(self, ip_list, parent=None):
        QLabel.__init__(self, parent)

        self.setTextFormat(Qt.RichText)
        self.setTextInteractionFlags(
            Qt.TextSelectableByKeyboard|Qt.TextSelectableByMouse
            )
        self.setFrameStyle(QFrame.StyledPanel)

        display_list = [unicode(ip) for ip in ip_list]
        display_list.sort()
        text = "<br/>".join(display_list)
        self.setText(text)

    def mouseDoubleClickEvent(self, event):
        QLabel.mouseDoubleClickEvent(self, event)
        self.emit(SIGNAL('double click'))

class CenteredCheckBox(QWidget):
    """Widget with a checkbox attribute: use self.checkbox to access the
    actual checkbox."""
    def __init__(self, parent=None):
        QWidget.__init__(self)
        self.setParent(parent)
        layout = QHBoxLayout(self)
        self.checkbox = QCheckBox(self)
        layout.addWidget(self.checkbox)
        layout.setContentsMargins(12, 0, 0, 0)  # Hack to correct offset.
        layout.setAlignment(Qt.AlignCenter)
        self.setLayout(layout)

class ConfigGroup(QGroupBox):
    def __init__(self, title, parent=None):
        QGroupBox.__init__(self, title, parent)
        self.form = QFormLayout(self)
        self.setStyleSheet(u"QGroupBox {font: bold italic large;}")

class SelectableLabel(QLabel):
    def __init__(self, text=u'', parent=None):
        QLabel.__init__(self, text, parent)
        self.setTextInteractionFlags(Qt.TextSelectableByKeyboard |
                                     Qt.TextSelectableByMouse)

