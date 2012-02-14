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


from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QFrame

from ufwi_rpcd.common.radius_client import RadiusServer
from ufwi_rpcc_qt.radius import RadiusFrame

from .directory_widget import DirectoryWidget

class RadiusUserWidget(DirectoryWidget):
    def __init__(self, config, specific_config, mainwindow, parent=None):
        DirectoryWidget.__init__(self, config, specific_config, mainwindow, parent=None)
        self.__setupgui()
        self.__setupsignals()

        if len(self.specific_config.servers) == 0:
            self.specific_config.servers.append(RadiusServer())

        self.updateView()

    def __setupgui(self):
        self.__radiusframe = RadiusFrame(self.mainwindow.client)
        self.__radiusframe.setFrameStyle(QFrame.NoFrame)
        self.form.addRow(self.__radiusframe)
        self.__radiusframe.show()

    def __setupsignals(self):
        for lineedit in self.__radiusframe.lineedits:
            self.connect(
                lineedit,
                SIGNAL("textEdited(QString)"),
                self.signalModified
                )

    def signalModified(self):
        self.specific_config.servers = [self.__radiusframe.getRadiusserverconf(),]
        self.config.auth = self.specific_config
        DirectoryWidget.signalModified(self)

    def updateView(self):
        if len(self.specific_config.servers) == 0:
            self.specific_config.servers.append(RadiusServer())
        self.__radiusframe.setRadiusserverconf(
            self.specific_config.servers[0]
            )

