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


from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QAction
from PyQt4.QtGui import QColor
from PyQt4.QtGui import QFrame
from PyQt4.QtGui import QIcon
from PyQt4.QtGui import QLabel
from PyQt4.QtGui import QMenu
from PyQt4.QtGui import QMessageBox
from PyQt4.QtGui import QPalette
from PyQt4.QtGui import QScrollArea
from PyQt4.QtGui import QVBoxLayout
from PyQt4.QtGui import QWidget

from ufwi_rpcd.common import tr
from ufwi_rpcc_qt.colors import COLOR_ERROR
from ufwi_conf.client.qt.foldable_widget import FoldableWidget
from ufwi_conf.client.qt.message_area import MessageArea
from ufwi_conf.client.qt.toolbar import ToolBar
from ufwi_conf.client.qt.widgets import ScrollArea
from ufwi_conf.client.system.network.iface_widget import FoldableInterface, InterfaceDetails
from ufwi_conf.client.system.network.wizards import BondingWizard
from ufwi_conf.client.system.network.wizards import IfaceEditor
from ufwi_conf.client.system.network.wizards import VlanWizard
from ufwi_conf.client.system.network.wizards.network import NetworkWizard
from ufwi_conf.client.system.priorities import NETWORK_PRIORITY
from ufwi_conf.common.net_exceptions import NetCfgError
from ufwi_conf.common.net_interfaces import Bonding
from ufwi_conf.common.net_interfaces import Ethernet
from ufwi_conf.common.net_interfaces import Vlan
from ufwi_conf.common.net_base import hasIPConfiguration

from .qnet_object import QNetObject
from .protect_connection import Protector

class IfacesFrontend(ScrollArea):
    COMPONENT = 'network'
    LABEL = tr('Networks')
    REQUIREMENTS = ('network',)
    ICON = ':/icons/carte_reseau.png'

    def __init__(self, client, parent=None):
        ScrollArea.__init__(self)
        self._modified = False

        self.drawGUIBasic()

        self.loaded_done = False

        parent.widgets["Network"] = self
        parent.addToInfoArea(self.tr("Network configuration interface enabled"))

        self.new_vlan = QAction(QIcon(":/icons/vlan"), tr("New VLAN"), self)
        self.new_vlan.setToolTip(tr("Create a VLAN interface"))

        self.new_bonding = QAction(QIcon(":/icons/New_bonding"), tr("New Bonding"), self)
        self.new_bonding.setToolTip(tr("Create a Bonding interface"))

        self.new_network = QAction(QIcon(":/icons/addnetwork"), tr("New Network"), self)
        self.new_network.setToolTip(tr("Add a network definition"))

        self.show_all = QAction(QIcon(":/icons/show_all_interface"), tr("Text Set Below"), self)
        self.show_all.setToolTip(tr("Show all interfaces"))
        self.is_showing_all = False
        self.toggleShowAll()

        self.connect(self.show_all, SIGNAL('triggered(bool)'), self.toggleShowAll)

        self.contextual_toolbar = ToolBar(
            (
                self.new_network,
                self.new_vlan,
                self.new_bonding,
                self.show_all
            ),
            name=tr("Interfaces"))
        self.contextual_toolbar.setObjectName("Network toolbar")

        self.parent = parent
        self.client = client
        self.routes_model = None
        self.q_netobject = QNetObject.getInitializedInstance(self.client)
        self.q_netobject.registerCallbacks(
            self.canHandleModification,
            self.handleModification
            )

        if self.q_netobject.netcfg is None:
            self.parent.addToInfoArea("Could not load network configuration", COLOR_ERROR)
            msg_area = MessageArea()
            msg_area.setMessage(
                tr("Network configuration interface disabled"),
                tr("Could not fetch network configuration from the appliance"),
                "critical"
                )
            self.widget().layout().addWidget(msg_area)
            return
        self.resetConf()

        try:
            Protector(self.client.host, self)
        except:
            self.parent.addToInfoArea(
                tr(
                    "Problem while loading a misconfiguration preventer: "
                    "you will not be warned if you deconfigure the IP address "
                    "to which EdenWall Administration Suite is connected.")
                    )


    def canHandleModification(self):
        return True

    def handleModification(self):
        self.updateView()

    def drawGUIBasic(self):
        base = QWidget()
        box = QVBoxLayout(base)

        #panel title
        title = QFrame()
        title_layout = QVBoxLayout(title)
        title_label = QLabel("<h1>%s</h1>" % tr("Network configuration"))
        title_layout.addWidget(title_label)
        box.addWidget(title)

        self.active_part = QScrollArea()

        box.addWidget(self.active_part)
        self.setWidgetResizable(True)

        self.setWidget(base)


    def isModified(self):
        return self._modified

    def setModified(self, message):
        self._modified = bool(message)
        if self._modified:
            self.parent.setModified(self, True)
        if isinstance(message, (str, unicode)):
            self.parent.addToInfoArea(message)
        self.emit(SIGNAL("modified"))
        if message and self.isLoaded():
            self.q_netobject.post_modify()

    def updateView(self):
        self.ifaces_list.updateView()

    def resetConf(self):
        self.ifaces_list = IfacesWidget(self.client, self.new_network, self.new_vlan, self.new_bonding, self)
        self.active_part.setWidget(self.ifaces_list)
        self.active_part.setWidgetResizable(True)

        self.connect(self.new_network, SIGNAL('triggered(bool)'), self.ifaces_list.new_network)
        self.new_vlan.setEnabled(self.ifaces_list.canCreateNetwork())

        self.connect(self.new_vlan, SIGNAL('triggered(bool)'), self.ifaces_list.new_vlan)
        self.new_vlan.setEnabled(self.ifaces_list.canCreateVlan())

        self.connect(self.new_bonding, SIGNAL('triggered(bool)'), self.ifaces_list.new_bonding)
        self.new_bonding.setEnabled(self.ifaces_list.canCreateBonding())

        self.parent.writeAccessNeeded(self.new_network, self.new_vlan,
            self.new_bonding, self.show_all)

        self.connect(self.ifaces_list, SIGNAL("modified"), self.updateView)
        self.connect(self.ifaces_list, SIGNAL("modified"), self.msgArea)

        self._modified = False

    def msgArea(self, *args):
        if len(args) > 0:
            self.parent.addToInfoArea(args[0])

    def toggleShowAll(self, *args):
        #toggling value)
        self.is_showing_all ^= True
        text = tr("Show All Interfaces") if self.is_showing_all else tr("Show Only Configurable Interfaces")
        self.show_all.setText(text)
        self.emit(SIGNAL('show all'), not self.is_showing_all)

    def checkConf(self):
        #Done internally
        pass

    def saveConf(self, message):
        self.ifaces_list.save(message)
        self.resetConf()

    def get_addresses(self):
        return list(self.q_netobject.netcfg.iterAddresses())

    def loaded(self):
        self.loaded_done = True

    def isLoaded(self):
        return self.loaded_done

    @classmethod
    def get_priority(cls):
        return NETWORK_PRIORITY

class IfacesWidget(QWidget):
    def __init__(self, client, action_network, action_vlan, action_bonding, frontend):
        QWidget.__init__(self, frontend)
        self.setContentsMargins (15 , 15, 15, 15)
        self.setStyleSheet("IfacesWidget {background-color: #d7d7d7;}")

        self.frontend = frontend
        self.client = client
        self.action_new_network = action_network
        self.action_new_vlan = action_vlan
        self.action_new_bonding = action_bonding

        self.q_netobject = QNetObject.getInitializedInstance(self.client)
        self.connect(self.q_netobject, SIGNAL('cancelled'), self.updateView)

        self.ifaces2widgets = dict()
        self.ifaces = []

        self.interfaces_list = None

        self.updateData()
        self.mkLayout()
        self.updateView()

    def updateToolbar(self, *args):
        for button, method in (
            (self.action_new_vlan, self.canCreateVlan),
            (self.action_new_bonding, self.canCreateBonding),
            ):
            button.setEnabled(method())

    def canCreateVlan(self):
        return self.q_netobject.netcfg.canCreateVlan()

    def canCreateBonding(self):
        return self.q_netobject.netcfg.canCreateBonding()

    def canCreateNetwork(self):
        return self.q_netobject.netcfg.canCreateNetwork()

    def new_vlan(self, val):
        wizard = VlanWizard()
        self.connect(wizard, SIGNAL("modified"), self.ifaceEdited)
        wizard.exec_()

    def new_network(self):
        wizard = NetworkWizard(None)
        return_code = wizard.exec_()
        if return_code == 0:
            return

        interface = wizard.getInterface()
        interface_widget = self.ifaces2widgets[interface].content
        interface_widget.netwizardDone(wizard)

    def new_bonding(self, val):
        wizard = BondingWizard()
        self.connect(wizard, SIGNAL("modified"), self.ifaceEdited)
        wizard.exec_()
        self.updateToolbar()

    def setModified(self, bool=True):
        self.frontend.setModified(bool)
        self.updateToolbar()

    def checkNetLabelUnique(self, label, net):
        if label == "":
            return True
        try:
            found_net = self.q_netobject.netcfg.getNetByLabel(label)
        except:
            return True
        if found_net is net:
            return True
        raise NetCfgError(tr("Net label already used"))

    def save(self, message):
        netcfg_repr = self.q_netobject.netcfg.serialize()
        self.client.call('network', 'setNetconfig', netcfg_repr, message)
        self.setModified(False)

    def updateData(self):
        if self.frontend.isLoaded():
            self.q_netobject.fetch_data(self.client)
            self.emit(SIGNAL('netcfg_update'))
        try:
            self.ethtool_data = self.client.call('network', 'ethtool_digest_all')
        except Exception:
            #We can live without eth statistics
            self.ethtool_data = {}
        self.setModified(False)

    def editIface(self, iface):
        dialog = IfaceEditor(iface)
        self.connect(dialog, SIGNAL("modified"), self.ifaceEdited)
        if dialog.exec_():
            self.ifaceEdited(
                tr("Modified properties of interface '%(FULLNAME)s'.") %
                {'FULLNAME': iface.fullName()}
            )


    def ifaceEdited(self, message):
        self.updateView()
        self.setModified(message)

    def deleteInterface(self, iface):
        if isinstance(iface, (Vlan, Bonding)):
            delete_text, confirm_text, message = \
                self.tr("About to delete a network interface"), \
                self.tr("Confirm the deletion of a network interface"), \
                self.tr("Deleted interface %1").arg(iface.fullName())
        elif isinstance(iface, Ethernet):
            delete_text, confirm_text, message = \
                self.tr("About to delete the configuration of a network interface"), \
                self.tr("Confirm the network interface configuration deletion"), \
                self.tr("Deleted the configuration of the %1 interface").arg(iface.user_label)
        confirm = QMessageBox.warning(
            self, delete_text,
            self.tr(confirm_text),
            QMessageBox.Cancel, QMessageBox.Ok
            )

        if confirm != QMessageBox.Ok:
            return

        self.q_netobject.netcfg.removeInterface(iface)
        self.ifaces2widgets[iface].close()
        self.emit(SIGNAL('modified'), message)
        self.setModified(True)

    def newNet(self, iface):
        self.ifaces2widgets[iface].content.netWizard()

    def mkEditMenu(self, interface):

        def deleteIntermediate(value):
            self.deleteInterface(interface)
            self.updateToolbar()

        def editIntermediate(value):
            self.editIface(interface)
            self.updateToolbar()

        edit_interface = QAction(QIcon(":icons/edit"), tr("Edit interface parameters"), self)
        self.connect(edit_interface, SIGNAL('triggered(bool)'), editIntermediate )

        actions = [edit_interface]

        if interface.freeForIp():
            def addNetIntermediate(value):
                self.newNet(interface)
                self.updateToolbar()

            add_net = QAction(QIcon(":icons/addnetwork"), tr("Add a network to this interface"), self)
            self.connect(add_net, SIGNAL('triggered(bool)'), addNetIntermediate )

            actions.append(add_net)

        propose_del_action = True
        if isinstance(interface, Ethernet):
            if hasIPConfiguration(interface):
                del_message = tr("Delete configuration")
            else:
                propose_del_action = False
        else:
            del_message = tr("Delete this interface")

        if interface.hasHA():
            propose_del_action = False

        if propose_del_action:
            del_interface = QAction(QIcon(":icons/delete"), del_message, self)
            self.connect(del_interface, SIGNAL('triggered(bool)'), deleteIntermediate)
            actions.append(del_interface)

        menu = QMenu(self)
        menu.setObjectName("menu_%s" % interface.fullName())
        for action in actions:
            menu.addAction(action)

        return menu

    def closeEvent(self, event):
        self.disconnect(self.box_layout, SIGNAL('destroyed()'), self._updateView)
        QWidget.closeEvent(self, event)


    def mkLayout(self):
        self.box_layout = QVBoxLayout(self)
        self.box_layout.setMargin(0)
        self.box_layout.setAlignment(Qt.AlignTop)
        self.box_layout.addStretch()

    def updateView(self, *args):
        #Housekeeping
        for widget in self.ifaces2widgets.values():
            widget.deleteLater()
        self.ifaces2widgets.clear()

        #fetch data
        ifaces = list(self.q_netobject.netcfg.iterInterfaces())
        ifaces.sort()
        ifaces.reverse()

        #build widgets
        for index, iface in enumerate(ifaces):
            interface_data = FoldableInterface(iface)
            interface_data.setMenu(self.mkEditMenu(iface))
            if isinstance(interface_data.content, InterfaceDetails):
                for net in interface_data.content.net2widget.itervalues():
                    self.frontend.parent.writeAccessNeeded(net.title.edit_button)

            interface_widget = FoldableWidget(interface_data, start_folded=False, parent=self)
            if iface.hasHA():
                palette = interface_widget.palette()
                palette.setColor(QPalette.Window, QColor('#eee3cb'))
                interface_widget.setPalette(palette)
                interface_widget.setHideable(False)

            interface_widget.setAutoFillBackground(True)
            interface_widget.setFoldable(iface.freeForIp())
            interface_widget.setImmutableVisibility(not self.frontend.is_showing_all)
            self.frontend.parent.writeAccessNeeded(interface_widget.title.edit_button)

            #tell the widget when it should show or not
            #for interfaces not able to do networking
            if (not iface.freeForIp()) or (not iface.hasHA()):
                interface_widget.connect(
                    self.frontend,
                    SIGNAL('show all'),
                    interface_widget.setImmutableVisibility
                    )

            #listen to modifications
            self.connect(interface_widget, SIGNAL('modified'), self.setModified)

            #non standard adding because we reuse the same layout every time
            self.box_layout.insertWidget(0, interface_widget)
            self.ifaces2widgets[iface] = interface_widget

    def updateInterfaceMenu(self, interface):
        title = self.ifaces2widgets[interface].title
        menu = self.mkEditMenu(interface)
        title.edit_button.setMenu(menu)

