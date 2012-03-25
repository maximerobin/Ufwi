
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

from PyQt4.QtGui import QToolBar
from PyQt4.QtCore import Qt

class ToolBar(QToolBar):
    def __init__(self, actions, parent=None, name = ''):
        if name:
            QToolBar.__init__(self, name, parent)
        else:
            QToolBar.__init__(self, parent)
        self.addSeparator()
        self.setMovable(False)
        self.setAllowedAreas(Qt.TopToolBarArea)
        self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        for action in actions:
            self.addAction(action)

