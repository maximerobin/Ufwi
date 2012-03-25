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
from PyQt4.QtGui import QCheckBox

from ufwi_rpcd.common.tools import abstractmethod

from .scrollarea import ScrollArea
from .message_area import MessageArea

class FullFeaturedScrollArea(ScrollArea):
    def __init__(self, client, parent):
        ScrollArea.__init__(self)
        self.client = client
        self.mainwindow = parent
        self._modified = False
        self.error_message = ''
        self._not_modifying = True
        self.config = None
        self._module_disabled = False

        self.resetConf(no_interface=True)

        self.buildInterface()
        self.updateView()

    def setModified(self, value=True):
        if value == self._modified:
            return
        if self._not_modifying:
            return

        self._modified = value

        if not self._modified:
            return

        self.emit(SIGNAL('modified'))
        self.mainwindow.setModified(self)

    @abstractmethod
    def buildInterface(self):
        pass

    @abstractmethod
    def setViewData(self):
        pass

    @abstractmethod
    def fetchConfig(self):
        pass

    @abstractmethod
    def isValid(self):
        pass

    @abstractmethod
    def sendConfig(self, message):
        pass

    def resetConf(self, no_interface=False):
        self.fetchConfig()
        self._modified = False
        if no_interface:
            return
        self.updateView()

    def saveConf(self, message):
        self.sendConfig(message)
        self._modified = False

    def updateView(self):
        self._not_modifying = True
        self.setViewData()
        self._not_modifying = False

    def isModified(self):
        return self._modified

    #util
    def mkCheckBox(self, title):
        checkbox = QCheckBox(title)
        self.connect(checkbox, SIGNAL('stateChanged(int)'), lambda state: self.setModified())
        return checkbox


    def _disable(self, title, message, main_message):
        if self._module_disabled:
            #already done
            return
        self._module_disabled = True
        msg = MessageArea()
        msg.setMessage(
            title,
            message,
            "critical"
            )
        msg.setWidth(65)
        self.setWidget(msg)
        self.mainwindow.addToInfoArea(
            main_message
            )
        self.setWidgetResizable(True)
