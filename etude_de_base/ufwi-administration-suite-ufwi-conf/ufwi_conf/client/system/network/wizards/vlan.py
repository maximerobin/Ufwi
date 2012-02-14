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
from PyQt4.QtGui import QFormLayout
from PyQt4.QtGui import QPixmap
from PyQt4.QtGui import QWizard
from PyQt4.QtGui import QWizardPage

from ufwi_conf.client.system.network.vlan_editor import VlanEditor
from ufwi_conf.client.system.network.wizards.common import NetworkCommonWizard

from ..qnet_object import QNetObject

VLAN = 0

class VlanPage(QWizardPage):
    def __init__(self, editor, parent=None):
        QWizardPage.__init__(self, parent)

        self.vlan_editor = editor
        self.buildGUI()

        for item in (
            self.vlan_editor.vlan_id,
            self.vlan_editor.name
            ):
            self.connect(item, SIGNAL('textChanged(QString)'), self._completeChanged)

    def buildGUI(self):
        self.setTitle(self.tr("Create a VLAN interface"))
        self.setPixmap(QWizard.LogoPixmap, QPixmap(":/icons/vlan"))
        self.registerField("raw_device", self.vlan_editor.raw_device)
        self.registerField( "vlan_id", self.vlan_editor.vlan_id)
        self.registerField("vlan_name", self.vlan_editor.name)
        self.setSubTitle(self.tr("Please select an ethernet interface to use as a basis for your new VLAN interface"))
        form = QFormLayout(self)

        form.addRow(self.vlan_editor)

    def _completeChanged(self):
        self.emit(SIGNAL('completeChanged()'))

    def isComplete(self):
        return self.vlan_editor.isValid()

    def getUserLabel(self):
        return unicode(self.vlan_editor.name.text()).strip()

    def getVlanBase(self):
        return self.vlan_editor.raw_device.getSelection()

    def getVlanNumber(self):
        return self.vlan_editor.vlan_id.value()

    def validatePage(self):
        return self.vlan_editor.isValid()

    def nextId(self):
        #prevent "next"/"previous" buttons
        return -1

class VlanWizard(NetworkCommonWizard):
    def __init__(self, interface=None, parent=None):
        NetworkCommonWizard.__init__(self, parent=parent)

        self.q_netobject = QNetObject.getInstance()

        self.vlan_editor = VlanEditor(raw_device=interface)
        vlan_page = VlanPage(self.vlan_editor)
        vlan_page.validatePage()
        self._setPage(VLAN, vlan_page)

        self.connect(self.vlan_editor, SIGNAL('modified'), self.reemit)

    def accept(self):
        self.vlan_editor.accept()
        NetworkCommonWizard.accept(self)
        self.hide()


