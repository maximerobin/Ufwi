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

from PyQt4.QtGui import QIcon

from ufwi_rpcd.common import tr
from ufwi_rpcc_qt.tools import QDockWidget_setTab

def showLibrary(window, libraries):
    QDockWidget_setTab(window.dock_library)
    show = None
    visible = False
    for index, library in enumerate(libraries):
        if visible:
            show = library
            break
        if library.toolboxVisible():
            visible = True
    if not show:
        show = libraries[0]
    show.showToolbox()

def fillDecisionCombo(combo):
    combo.clear()
    combo.addItem(QIcon(":/icons-32/go-next.png"), tr("ACCEPT"))
    combo.addItem(QIcon(":/icons-32/drop.png"), tr("DROP"))
    combo.addItem(QIcon(":/icons-32/reject.png"), tr("REJECT"))

