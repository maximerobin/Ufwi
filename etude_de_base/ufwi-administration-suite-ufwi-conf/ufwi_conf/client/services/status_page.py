# -*- coding: utf-8 -*-

# $Id$

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


from PyQt4.QtGui import QFormLayout, QLabel, QGroupBox, QVBoxLayout

from ufwi_rpcd.common import tr
from ufwi_conf.client.services.dock_windows.monitor import MonitorWindow
from ufwi_conf.client.qt.widgets import ScrollArea

class StatusPage(ScrollArea):
    COMPONENT = 'status'
    LABEL = tr('Status')
    REQUIREMENTS = ('status',)
    ICON = ':/icons/info.png'

    def __init__(self, client, parent):
        ScrollArea.__init__(self)

        self.client = client
        self.mainwindow = parent
        self.form = QFormLayout(self)

        title = QLabel("<H1>Services</H1>")
        self.form.addRow(title)

        self.monitor = None
        group = QGroupBox()
        group.setTitle(self.tr("System Services Status"))
        box = QVBoxLayout(group)
        #parent is expected to be MainWindow !
        self.monitor = MonitorWindow(client, self, parent)
        box.addWidget(self.monitor)
        self.form.addRow(group)

    @staticmethod
    def get_calls():
        """
        services called by initial multicall
        """
        # for first refresh inside MonitorWindow
        return ( ('status', 'getStatus'), )

    def isModified(self):
        return False
