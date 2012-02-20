
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
from PyQt4.QtCore import Qt
from PyQt4.QtGui import QFrame
from PyQt4.QtGui import QListWidgetItem

from .qnet_object import QNetObject
from ufwi_conf.client.system.network.bonding_ui import Ui_Bonding

class IfaceItem(QListWidgetItem):
    def __init__(self, iface, parent=None):
        self.iface = iface
        QListWidgetItem.__init__(self, iface.hard_label, parent, QListWidgetItem.UserType)


class BondingEditor(QFrame, Ui_Bonding):
    def __init__(self, bonding=None, parent=None):
        QFrame.__init__(self, parent)
        self.setupUi(self)
        self.bonding = bonding

        self.fetchAndFill(bonding)

        self.connect(self.add, SIGNAL('clicked()'), self.addIface)
        self.connect(self.remove, SIGNAL('clicked()'), self.removeIface)
        self.connect(self.available, SIGNAL('itemSelectionChanged()'), self.availableSelectionChanged)
        self.connect(self.selected, SIGNAL('itemSelectionChanged()'), self.selectedSelectionChanged)

    def fetchAndFill(self, bonding):
        activables = list(QNetObject.getInstance().netcfg.iterAggregables())
        for iface in activables:
            self.available.addItem(IfaceItem(iface))

        if bonding is None:
            return

        for ethernet in bonding.ethernets:
            self.selected.addItem(IfaceItem(ethernet))

        self.user_label.setText(bonding.user_label)


    def availableSelectionChanged(self):
        enable = len(self.available.selectedItems()) > 0
        self.add.setEnabled(enable)
        self.selected.clearSelection()

    def selectedSelectionChanged(self):
        enable = len(self.selected.selectedItems()) > 0
        self.remove.setEnabled(enable)
        self.available.clearSelection()

    def addIface(self):
        self._transfer(self.available, self.selected)

    def removeIface(self):
        self._transfer(self.selected, self.available)

    def _transfer(self, giver, receiver):
        selection = giver.currentItem()
        receiver.addItem(IfaceItem(selection.iface))
        giver.takeItem(giver.currentRow())

    def setName(self):
        new_name = self.user_label.text()
        new_name = unicode(new_name).strip()
        if new_name != self.bonding.user_label:
            self.bonding.user_label = new_name

    def getSelected(self):
        return (item.iface for item in self.selected.findItems("*", Qt.MatchWildcard))

    def accept(self):
        selected = list(self.getSelected())
        if len(selected) == 0:
            return False

        self.setName()
        self.bonding.ethernets = selected
        self.emit(SIGNAL('edited'), "edited bonding interface '%s'" % self.bonding.fullName())
        self.emit(SIGNAL('modified'), "edited bonding interface '%s'" % self.bonding.fullName())
        return True
