
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
from PyQt4.QtGui import QWizardPage
from PyQt4.QtGui import QMessageBox
from PyQt4.QtGui import QVBoxLayout

from ufwi_rpcd.common import tr
from ufwi_conf.common.net_exceptions import NetCfgError
from ufwi_conf.client.system.network.wizards.common import NetworkCommonWizard
from ufwi_conf.client.system.network.bonding_editor import BondingEditor

from ..qnet_object import QNetObject

BONDING = 0


class BondingPage(QWizardPage):
    def __init__(self, q_netobject, parent=None):
        QWizardPage.__init__(self, parent)
        self.q_netobject = q_netobject

        self.setTitle(self.tr("Bonding interface configuration"))
        self.setSubTitle(self.tr("Please select the ethernet interfaces to aggregate"))
        box = QVBoxLayout(self)
        self.frame = BondingEditor()
        box.addWidget(self.frame)
        self.registerField('user label', self.frame.user_label)
        self.registerField('selected', self.frame.selected)

    def getUserLabel(self):
        return unicode(self.field('user label').toString()).strip()

    def validatePage(self):
        selected = list(self.frame.getSelected())
        user_label = self.getUserLabel()
        try:
            new_bonding = self.q_netobject.netcfg.createBonding(user_label, selected)
        except NetCfgError, err:
            QMessageBox.warning(self, tr("Could not create bonding interface"), err.message)
            return False
        self.emit(SIGNAL('modified'), tr("New bonding interface created: \"%s\"") % new_bonding.fullName())
        return True

    def nextId(self):
        return -1

class BondingWizard(NetworkCommonWizard):
    def __init__(self, parent=None):
        NetworkCommonWizard.__init__(self, parent=None)
        self.q_netobject = QNetObject.getInstance()

        bonding_page = BondingPage(self.q_netobject)
        self._setPage(BONDING, bonding_page)
