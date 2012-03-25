# -*- coding: utf-8 -*-

"""
Copyright (C) 2008-2011 EdenWall Technologies
Written by Sebastien Tricaud <stricaud@inl.fr>

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

from PyQt4.QtGui import QFontMetrics, QTextEdit
from PyQt4.QtCore import QSize

class InfoArea:
    # Default behavior, no lock.
    lock = False

    def __init__(self, parent):

        self.p = parent

        while self.p and (not hasattr(self.p, 'ui') or not hasattr(self.p.ui, 'info_area')):
            self.p = self.p.parent()

        if not self.p:
            self.ui = None
        else:
            self.ui = self.p.ui
            self.setHeight()

    def lockArea(self):
        InfoArea.lock = True

    def unlockArea(self):
        InfoArea.lock = False

    def setText(self, text):
        if not InfoArea.lock and self.ui:
            self.ui.info_area.text = text
            self.ui.info_area.refreshText()

    def setGlobalFilter(self, text):
        if not self.ui:
            return
        self.ui.info_area.filter = text
        self.ui.info_area.refreshText()

    def setHeight(self):
        # Set a fixed height equivalent to 3 lines of text:
        if not self.ui:
            return
        line_height = QFontMetrics(self.ui.info_area.font()).height()
        self.ui.info_area.setMaximumHeight(10 * line_height)

class InfoAreaWidget(QTextEdit):
    def __init__(self, parent):
        QTextEdit.__init__(self, parent)
        self.text = ""
        self.filter = ""

    def sizeHint(self):
        return QSize(-1, 200)

    def refreshText(self):
        self.clear()
        self.insertHtml(self.filter + "</br>" + self.text)
