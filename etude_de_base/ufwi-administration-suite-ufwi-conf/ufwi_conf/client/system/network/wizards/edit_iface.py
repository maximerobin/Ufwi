
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
from PyQt4.QtGui import QWizard
from PyQt4.QtGui import QPixmap
from PyQt4.QtGui import QWizardPage
from PyQt4.QtGui import QVBoxLayout

from ufwi_rpcd.common import tr
from ufwi_conf.common.net_interfaces import Vlan
from ufwi_conf.common.net_interfaces import Bonding
from ufwi_conf.common.net_interfaces import Ethernet
from ufwi_conf.client.system.network.vlan_editor import VlanEditor
from ufwi_conf.client.system.network.bonding_editor import BondingEditor
from ufwi_conf.client.system.network.ethernet_editor import EthernetEditor
from ufwi_conf.client.system.network.qnet_object import QNetObject
from .common import NetworkCommonWizard

class OnlyPage(QWizardPage):
    def __init__(self, iface, parent=None):
        QWizardPage.__init__(self, parent)

        self.setTitle(tr("Edit interface parameters"))
        self.setSubTitle(tr("Interface name"))

        self.q_netobject = QNetObject.getInstance()

        layout = QVBoxLayout(self)
        if isinstance(iface, Vlan):
            self.editor = VlanEditor(vlan=iface)
            self.setPixmap(QWizard.LogoPixmap, QPixmap(":/icons/vlan"))
        elif isinstance(iface, Bonding):
            self.editor = BondingEditor(bonding=iface)
        elif isinstance(iface, Ethernet):
            self.editor = EthernetEditor(iface)
        self.validatePage = self.editor.accept
        layout.addWidget(self.editor)

        self.connect(self.editor, SIGNAL("modified"), self.resendModified)

    def resendModified(self, *args):
        self.emit(SIGNAL("modified"), *args)
        #form = QFormLayout(self)
        #self.user_label = TextWithDefault(iface.user_label)
        #self.registerField("label", self.user_label)
        #form.addRow("Specify interface label", self.user_label)

    def validatePage(self):
        return True

class IfaceEditor(NetworkCommonWizard):
    def __init__(self, iface, parent=None):
        NetworkCommonWizard.__init__(self, parent=parent)
        self.setOption(QWizard.NoBackButtonOnStartPage, True)
        page = OnlyPage(iface)
        self.addPage(page)
        self.connect(page, SIGNAL("modified"), self.resendModified)

    def resendModified(self, *args):
        self.emit(SIGNAL("modified"), *args)


