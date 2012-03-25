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


from PyQt4.QtCore import QVariant
from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QComboBox
from PyQt4.QtGui import QVBoxLayout
from PyQt4.QtGui import QWizardPage

from ufwi_rpcd.client import tr
from ufwi_conf.client.system.network.wizards.common import NetworkCommonWizard
from ufwi_conf.client.system.network.net_editor import NetFrame
from ufwi_conf.client.system.network.qnet_object import QNetObject

class InterfacePage(QWizardPage):
    """
    Allows the user to choose one among networkable interfaces to build a net upon.
    """
    def __init__(self, parent=None):
        QWizardPage.__init__(self, parent)
        self.__make_gui()
        self.__populate()
        self.connect(self.__dropdown, SIGNAL("currentIndexChanged(int)"), self.propagate)

    def __make_gui(self):
        self.setTitle(tr("Network Editor"))
        self.setSubTitle(tr("Select the interface to which you want to add a network"))
        box = QVBoxLayout(self)
        self.__dropdown = QComboBox()
        box.addWidget(self.__dropdown)

    def __candidates(self):
        candidates = list(
            QNetObject.getInstance().netcfg.iterNetworkables()
            )
        candidates.sort()
        return candidates

    def __populate(self):
        candidates = self.__candidates()
        for interface in candidates:
            variant = QVariant(interface)
            self.__dropdown.addItem(interface.fullName(), variant)

    def propagate(self):
        """
        propagate: emits a "changed" SIGNAL with the chosen interface as content
        """
        self.emit(SIGNAL("changed"), self.interface())

    def interface(self):
        """
        returns the currently selected interface
        """
        #QVariant with custom content
        variant = self.__dropdown.itemData(
            self.__dropdown.currentIndex()
            )
        interface = variant.toPyObject()
        return interface

    def setInterface(self, target):
        for index in xrange(self.__dropdown.count()):
            variant = self.__dropdown.itemData(index)
            interface = variant.toPyObject()
            if interface is target:
                break
        self.__dropdown.setCurrentIndex(index)


class NetPage(QWizardPage):
    def __init__(self, editor, parent=None):
        QWizardPage.__init__(self, parent)

        self.editor = editor

        self.setTitle(tr("Network Editor"))
        self.setSubTitle(tr("Set network parameters below"))
        box = QVBoxLayout(self)
        box.addWidget(self.editor)

    def validatePage(self):
        return self.editor.isValid()

class NetworkWizard(NetworkCommonWizard):
    def __init__(self, interface, parent=None):
        NetworkCommonWizard.__init__(self, parent)
        self.editor = NetFrame(interface)
        self.interface_page = InterfacePage()
        self._setPage(0, self.interface_page)
        self.net_page = NetPage(self.editor)
        self._setPage(1, self.net_page)
        self.connect(self.interface_page, SIGNAL('changed'), self.editor.setInterface)

        if interface is not None:
            self.setStartId(1)
            #Todo: find a way to allow going back
            self.interface_page.setInterface(interface)
        else:
            self.interface_page.propagate()

        self.connect(self, SIGNAL('accepted()'), self._done)

    def getNet(self):
        return self.editor.getNet()

    def getInterface(self):
        return self.interface_page.interface()

    def _done(self, *args):
        self.emit(SIGNAL('done'), self)
        QNetObject.getInstance().post_modify()

