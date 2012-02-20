
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

from PyQt4.QtGui import (
    QWizard, QWizardPage, QLabel, QFormLayout, QComboBox, QButtonGroup, QMessageBox,
    QRadioButton, QSpinBox, QFrame, QHBoxLayout, QPixmap, QVBoxLayout, QLineEdit, QListWidgetItem
    )
from PyQt4.QtCore import Qt, SIGNAL

from ufwi_rpcd.common import tr
from ufwi_rpcd.common.error import exceptionAsUnicode

from ufwi_conf.common.net_exceptions import NetCfgError
from ufwi_conf.client.system.network.bonding_ui import Ui_Bonding

from .qnet_object import QNetObject

INTRO, ETHERNET_IFACE, VLAN_IFACE, BONDING_IFACE = xrange(4)

class IfaceItem(QListWidgetItem):
    def __init__(self, iface, parent=None):
        self.iface = iface
        QListWidgetItem.__init__(self, iface.hard_label, parent, QListWidgetItem.UserType)

class HelpMissingFunction(QFrame):
    def __init__(self, text, parent=None):
        QFrame.__init__(self, parent)
        self.setFrameStyle(QFrame.StyledPanel)
        layout = QHBoxLayout(self)
        icon = QLabel()
        icon.setPixmap(QPixmap(":/icons-32/info"))
        layout.addWidget(icon)
        message = QLabel(text)
        message.setWordWrap(True)
        layout.addWidget(message)
        layout.addStretch()

class IfaceWizardPage(QWizardPage):
    def __init__(self, ifaces_list, parent=None):
        QWizardPage.__init__(self, parent)
        self.setTitle("Network interface configuration")

class VlanOnlyIntro(IfaceWizardPage):
    def __init__(self, parent=None):
        IfaceWizardPage.__init__(self, parent)
        self.setSubTitle("Vlan Configuration")
        layout = QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(
            HelpMissingFunction("""\
All ethernet interfaces are either used directly or in Vlans/bondings.

In order to be able to activate an ethernet interface for direct use or \
for bonding agregation, you must deconfigure existing interfaces first""")
        )

    def nextId(self):
        return VLAN_IFACE

class VlanEthernetIntro(IfaceWizardPage):
    def __init__(self, iface_name, parent=None):
        IfaceWizardPage.__init__(self, parent)
        self.q_netobject = QNetObject.getInstance()
        self.setSubTitle("What kind of interface do you want to configure?")
        box = QVBoxLayout(self)

        self.ethernet = "ethernet", "Activate ethernet interface %s" % iface_name , QRadioButton()
        self.vlan = "vlan", "Create a VLAN interface", QRadioButton()

        group = QButtonGroup(self)
        form = QFormLayout()

        options = (self.ethernet, self.vlan)

        for item in options:
            group.addButton(item[2])
            form.addRow(item[1], item[2])
            self.registerField(item[0], item[2])


        self.ethernet[2].setChecked(Qt.Checked)

        box.addLayout(form)
        box.addStretch()

        box.addWidget(
            HelpMissingFunction("""\
All interfaces but one (%s) are configured.

In order to be able to activate an ethernet interface for bonding agregation, \
you must deconfigure at least one ethernet interface first \
(which may be in use by vlans or bondings).""" % iface_name)
        )

    def nextId(self):
        if self.field(self.ethernet[0]).toBool():
            return ETHERNET_IFACE
        if self.field(self.vlan[0]).toBool():
            return VLAN_IFACE
        return BONDING_IFACE

class Ethernet(IfaceWizardPage):
    def __init__(self, parent=None):
        IfaceWizardPage.__init__(self, parent)

        self.setTitle("Network interface configuration")
        self.setFinalPage(True)
        self._complete = True

        self.form = QFormLayout(self)
        self.user_label = QLineEdit()
        self.form.addRow("Please specify interface label", self.user_label)
        self.registerField("ethernet user_label", self.user_label)
        self.connect(self.user_label, SIGNAL('textChanged(QString)'), self.computeComplete)

    def computeComplete(self, *args):
        complete = self.isComplete()
        if self._complete == complete:
            self._complete = complete
            self.emit(SIGNAL('completeChanged()'))

    def nextId(self):
        return -1

    def getUserLabel(self):
        return unicode(self.field("ethernet user_label").toString()).strip()

    def isComplete(self):
        return  self.getUserLabel() != ""

    def validatePage(self, hard_label):
        """
        Compulsory subclassing.
        PyQt visible signature must be 'def validatePage(self)'
        """
        try:
            user_label = self.getUserLabel()
        except NetCfgError, err:
            QMessageBox.warning(self, "Invalid name", exceptionAsUnicode(err))
            return False
        self.q_netobject.netcfg.activateIface(hard_label, user_label)
        self.emit(
            SIGNAL('modified'),
            "Activated: <i>'%s'</i> with name <i>'%s'</i>" % (hard_label, user_label)
            )
        return True

class OneEthernet(Ethernet):
    def __init__(self, hard_label, parent=None):
        Ethernet.__init__(self, parent)

        self.setSubTitle("About to activate interface %s" % hard_label)
        self.hard_label = hard_label
        self.user_label.setText(hard_label)

    def validatePage(self):
        return Ethernet.validatePage(self, self.hard_label)

class ManyEthernet(Ethernet):
    def __init__(self, parent=None):
        Ethernet.__init__(self, parent)
        self.setSubTitle("Please select the ethernet interface to activate and name it.")

        ifaces_choice = QComboBox()
        self.index2iface = {}

        for index, item in enumerate(self.q_netobject.netcfg.iterVlanables()):
            ifaces_choice.addItem(item.user_label)
            self.index2iface[index] = item

        self.form.insertRow(0, "Select an ethernet interface", ifaces_choice)
        self.registerField("ethernet choice", ifaces_choice)

    def getEthernetSelection(self):
        return self.index2iface[self.field("ethernet choice").toInt()[0]]

    def validatePage(self):
        return Ethernet.validatePage(self, self.getEthernetSelection().hard_label)

class IfaceType(IfaceWizardPage):

    def __init__(self, parent=None):
        IfaceWizardPage.__init__(self, parent)
        self.setSubTitle("What kind of interface do you want to configure?")

        self.ethernet = "ethernet", "Activate ethernet interface", QRadioButton()
        self.vlan = "vlan", "Create a VLAN interface", QRadioButton()
        self.bonding = "bonding", QLabel("Create a bonding interface"), QRadioButton()

        group = QButtonGroup(self)
        form = QFormLayout(self)

        options = (self.ethernet, self.vlan, self.bonding)

        for item in options:
            group.addButton(item[2])
            form.addRow(item[1], item[2])
            self.registerField(item[0], item[2])

        self.ethernet[2].setChecked(Qt.Checked)


    def nextId(self):
        if self.field(self.ethernet[0]).toBool():
            return ETHERNET_IFACE
        if self.field(self.vlan[0]).toBool():
            return VLAN_IFACE
        return BONDING_IFACE

class Vlan(IfaceWizardPage):
    def __init__(self, vlanables, parent=None):
        IfaceWizardPage.__init__(self, parent)

        self.vlanables = tuple(vlanables)

        self.setSubTitle("Please select an ethernet interface to use as a basis for your new VLAN interface")
        form = QFormLayout(self)

        user_label = QLineEdit()
        form.addRow("Interface label", user_label)
        self.registerField("vlan name", user_label)

        ifaces_choice = QComboBox()
        self.names2ifaces = dict(
            ((iface.fullName(), iface) for iface in vlanables)
        )
        ifaces_choice.addItems(list(iface.fullName() for iface in vlanables))

        form.addRow("Select an ethernet interface", ifaces_choice)
        self.registerField("vlan base", ifaces_choice)

        vlan_number = QSpinBox()
        form.addRow("Specify Vlan ID", vlan_number)
        self.registerField("vlan number", vlan_number)

    def getUserLabel(self):
        return unicode(self.field('vlan name').toString()).strip()

    def getVlanBase(self):
        index = self.field('vlan base').toInt()[0]
        return self.vlanables[index]

    def getVlanNumber(self):
        return self.field("vlan number").toInt()[0]

    def validatePage(self):
        user_label = self.getUserLabel()
        vlan_base = self.getVlanBase()
        vlan_number = self.getVlanNumber()
        try:
            self.q_netobject.netcfg.createVlan(vlan_base, user_label, vlan_number)
        except NetCfgError, err:
            QMessageBox.warning(self, "Could not create vlan interface", exceptionAsUnicode(err))
            return False
        self.emit(SIGNAL('modified'), tr("New vlan interface created: <i>'%s'</i>") % user_label)
        return True

    def nextId(self):
        return -1

class BondingFrame(QFrame, Ui_Bonding):
    def __init__(self, activable, parent=None):
        QFrame.__init__(self, parent)
        self.setupUi(self)

        for iface in activable:
            self.available.addItem(IfaceItem(iface))
        self.connect(self.add, SIGNAL('clicked()'), self.addIface)
        self.connect(self.remove, SIGNAL('clicked()'), self.removeIface)
        self.connect(self.available, SIGNAL('itemSelectionChanged()'), self.availableSelectionChanged)
        self.connect(self.selected, SIGNAL('itemSelectionChanged()'), self.selectedSelectionChanged)

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

class Bonding(IfaceWizardPage):
    def __init__(self, parent=None):
        IfaceWizardPage.__init__(self, parent)

        self.setSubTitle("Please select the ethernet interfaces to aggregate")
        box = QVBoxLayout(self)
        self.frame = BondingFrame(list(self.q_netobject.netcfg.iterAggregables()))
        box.addWidget(self.frame)
        self.registerField('user label', self.frame.user_label)
        self.registerField('selected', self.frame.selected)

    def getSelected(self):
        return (item.iface for item in self.frame.selected.findItems("*", Qt.MatchWildcard))

    def getUserLabel(self):
        return unicode(self.field('user label').toString()).strip()

    def validatePage(self):
        selected = list(self.getSelected())
        user_label = self.getUserLabel()
        try:
            self.q_netobject.netcfg.createBonding(user_label, selected)
        except NetCfgError, err:
            QMessageBox.warning(self, "Could not create bonding interface", exceptionAsUnicode(err))
            return False
        self.emit(SIGNAL('modified'), tr("New bonding interface created: <i>'%s'</i>") % user_label)
        return True

    def nextId(self):
        return -1

class IfaceWizard(QWizard):
    def __init__(self, parent=None):
        QWizard.__init__(self, parent)
        self.setOption(QWizard.NoBackButtonOnStartPage, True)

        self.q_netobject = QNetObject.getInstance()

        vlanables = list(self.q_netobject.netcfg.iterVlanables())
        aggregables = list(self.q_netobject.netcfg.iterAggregables())

        vlanables_nb = len(vlanables)
        aggregables_nb = len(aggregables)

        vlanables.sort()
        if vlanables_nb + aggregables_nb == 0:
            QMessageBox.warning(
                self,
                "Flow error",
                "This wizard should not be available when there is no usable interface for it"
                )
            return

        self._setPage(VLAN_IFACE, Vlan(vlanables))

        if aggregables_nb == 0:
            self.setPage(INTRO, VlanOnlyIntro())
        elif aggregables_nb < 2:
            #Not offering the possibility of making a bonding
            if vlanables_nb == 1:
                hard_label = vlanables[0].hard_label
                self._setPage(INTRO, VlanEthernetIntro(hard_label))
                self._setPage(ETHERNET_IFACE, OneEthernet(hard_label))
            else:
                self._setPage(INTRO, VlanEthernetIntro(hard_label))
                self._setPage(ETHERNET_IFACE, ManyEthernet())
        else:
            self._setPage(INTRO, IfaceType())
            self._setPage(ETHERNET_IFACE, ManyEthernet())
            self._setPage(BONDING_IFACE, Bonding())

    def _setPage(self, index, page):
        self.setPage(index, page)
        self.connect(page, SIGNAL('modified'), self.reemit)


    def reemit(self, *args):
        self.emit(SIGNAL('modified'), *args)

