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


from IPy import IP
from functools import partial

from PyQt4.QtGui import (
    QVBoxLayout, QTableWidget, QPushButton, QIcon, QPixmap, QHeaderView,
    QAbstractItemView, QLabel)
from PyQt4.QtCore import SIGNAL, Qt

from ufwi_rpcd.client.error import RpcdError
from ufwi_rpcd.common import tr, EDENWALL
from ufwi_rpcc_qt.colors import COLOR_ERROR
from ufwi_rpcc_qt.services_name import ComponentToName

from ufwi_conf.client.qt.ufwi_conf_form import NuConfModuleDisabled
from ufwi_conf.client.qt.widgets import ScrollArea
from ufwi_conf.client.system.network import QNetObject
from ufwi_conf.common.access_cfg import AccessConf, OPEN_BY_DEFAULT, CLOSED_NETWORKS
from ufwi_conf.common.net_exceptions import NoMatch
if EDENWALL:
    from ufwi_conf.client.services.roadwarrior import QOpenVpnObject
    from ufwi_conf.common.openvpn_cfg import INTERFACE_NAME as OPENVPN_INTERFACE

class AccessFrontend(ScrollArea):
    COMPONENT = 'access'
    LABEL = tr('Access to services')
    REQUIREMENTS = ('access',)
    STYLE_ALLOW = "color: white; background-color: white; border: none;"
    STYLE_DISALLOW = "color: lightGray; background-color: lightGray; border: none;"
    ICON = ':/icons/Acl.png'

    def __init__(self, client, parent):
        ScrollArea.__init__(self)

        self.client = client
        self.mainwindow = parent
        self._modified = False
        self.__disabled = False
        self.net_object = QNetObject.getInitializedInstance(self.client)
        if EDENWALL:
            self.vpn_object = QOpenVpnObject.getInstance()

        self.setupWidgets()
        self.getConfigs()
        self.getNetworks()
        # vpn_config is used to check if the VPN config changed or not
        self.vpn_config = self.getVPNConfig()
        self.fillTable()
        self.net_object.registerCallbacks(self.validateNetCfg, self.updateWithNetCfg)
        if EDENWALL:
            self.vpn_object.registerCallbacks(self.validateVpnCfg, self.updateWithVpnCfg)


        self.mainwindow.addToInfoArea(tr("Access interface enabled"))

    @staticmethod
    def get_calls():
        """
        services called at startup (self.mainwindow.init_call)
        """
        return (('access', 'getConfig'),)

    def getVPNConfig(self):
        if not EDENWALL:
            return None
        vpn = self.vpn_object.getCfg()
        if not vpn:
            return None
        return (vpn.enabled, vpn.protocol, vpn.port, vpn.client_network)

    def setupWidgets(self):
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        self.icon = QIcon()
        ALLOW = QPixmap(":/icons-20/status_on.png")
        self.icon.addPixmap(ALLOW, QIcon.Normal, QIcon.On)
        DISALLOW = QPixmap(":/icons-20/status_off.png")
        self.icon.addPixmap(DISALLOW, QIcon.Normal, QIcon.Off)

        title = QLabel(u"<H1>%s</H1>" % tr("Access to services"))
        layout.addWidget(title)

        self.table = QTableWidget()
        self.table.setSelectionMode(QAbstractItemView.NoSelection)

        layout.addWidget(self.table)

    def isModified(self):
        return self._modified

    def isValid(self):
        if self.__disabled:
            return True
        valid, errmsg = self.access_cfg.isValidWithMsg()
        if not valid:
            self.error_message = errmsg
        return valid

    def setModified(self, modif=True):
        if self.__disabled:
            self._modified = False
            return
        self._modified = modif
        if modif:
            self.mainwindow.setModified(self, True)

    def resetConf(self):
        if self.__disabled:
            return
        self.getConfigs()
        self.getNetworks()
        self.fillTable()

    def __disable(self, reason):
        if self.__disabled:
            return
        self.__disabled = True
        self.mainwindow.addToInfoArea(
            tr("The Access to services interface is disabled."),
            COLOR_ERROR)
        self.mainwindow.addToInfoArea(reason, COLOR_ERROR)
        self.close()
        raise NuConfModuleDisabled(reason)

    def getConfigs(self):
        if self.__disabled:
            return
        try:
            data = self.mainwindow.init_call('access', 'getConfig')
        except RpcdError:
            self.__disable(tr("Could not get Access to services configuration."))
            return
        if data is None:
            self.access_cfg = AccessConf.defaultConf()
        else:
            self.access_cfg = AccessConf.deserialize(data)

    def _getNetworks(self, netcfg):
        return [(interface.system_name, network)
            for interface, network in netcfg.iterKnownNetworks()]

    def getNetworks(self):
        if self.__disabled:
            return
        netcfg = QNetObject.getInstance().netcfg
        if netcfg is None:
            self.networks = ()
            self.mainwindow.addToInfoArea(
                tr("The access interface could not load the network configuration"),
                COLOR_ERROR
                )
            return
        # list of (interface, network) where interface (str) is the system
        # name, and network (IPy.IP object) is the network address
        # (eg. IP('192.168.0.0/24')
        self.networks = self._getNetworks(netcfg)
        self.networks += list(self.access_cfg.custom_networks)
        self.networks.sort()

    def fillTable(self):
        if self.__disabled:
            self.table.clear()
            return
        services = list(self.access_cfg.permissions)
        self.table.clear()

        # (interface (str), network (IPy), ip version (int)) => row (int)
        # Don't use (interface, network) because of a bug in IPy < 0.70:
        # IP('0.0.0.0/0') and IP('::/0') are considered as equal
        self.net_to_row = {}

        component_to_name = ComponentToName()
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self.networks))
        self.setVerticalHeaders()
        self.table.setColumnCount(len(services))
        self.table.setHorizontalHeaderLabels([component_to_name.display_name(service) for service in services])
        self.table.horizontalHeader().setResizeMode(QHeaderView.ResizeToContents)

        for irow, interface_network in enumerate(self.networks):
            self.setRow(interface_network, irow)
            for icol, service in enumerate(self.access_cfg.permissions):
                allow = interface_network in self.access_cfg.permissions[service]
                self.createService(irow, icol, service, interface_network, allow)

    def getRow(self, interface_network, pop=False):
        interface, network = interface_network
        key = (interface, network, network.version())
        if pop:
            return self.net_to_row.pop(key)
        else:
            return self.net_to_row[key]

    def setRow(self, interface_network, row):
        interface, network = interface_network
        key = (interface, network, network.version())
        self.net_to_row[key] = row

    def setVerticalHeaders(self):
        labels = [self.netLabel(interface, network)
            for interface, network in self.networks]
        self.table.setVerticalHeaderLabels(labels)

    def saveConf(self, message):
        data = self.access_cfg.serialize(downgrade=True)
        self.client.call("access", 'setConfig', message, data)
        self.setModified(False)

    def changeService(self, col, service, interface_network):
        row = self.getRow(interface_network)
        self.setModified(True)
        button = self.table.cellWidget(row, col)
        if button.isChecked():
            self.access_cfg.permissions[service].add(interface_network)
            button.setStyleSheet(self.STYLE_ALLOW)
        else:
            try:
                self.access_cfg.permissions[service].remove(interface_network)
            except KeyError:
                pass
            button.setStyleSheet(self.STYLE_DISALLOW)

    def appendNetwork(self, interface_network, close_all_ports=False):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.networks.append(interface_network)
        self.setRow(interface_network, row)
        interface, network = interface_network
        for icol, service in enumerate(self.access_cfg.permissions):
            if (not close_all_ports) \
            and (service in OPEN_BY_DEFAULT) \
            and (network not in CLOSED_NETWORKS):
                allow = True
                self.access_cfg.permissions[service].add(interface_network)
            else:
                allow = interface_network in self.access_cfg.permissions[service]
            self.createService(row, icol, service, interface_network, allow)

    def removeNetwork(self, interface_network):
        index = self.getRow(interface_network, pop=True)
        self.table.removeRow(index)
        network = self.networks[index]
        for service, networks in self.access_cfg.permissions.iteritems():
            try:
                networks.remove(network)
            except KeyError:
                pass
        del self.networks[index]
        for key, row in self.net_to_row.iteritems():
            if row > index:
                self.net_to_row[key] -= 1

    # callback used to update the table on network modification
    def updateWithNetCfg(self, deleted_nets, added_nets):
        if not(deleted_nets or added_nets):
            return

        # delete
        for key in deleted_nets:
            self.removeNetwork(key)

        # add new
        for interface_network in added_nets:
            self.appendNetwork(interface_network, close_all_ports=True)

        # modify and update
        self.setVerticalHeaders()
        self.setModified(True)

    def createService(self, row, col, service, interface_network, allow):
        button = QPushButton(self.icon, u'')
        button.setCheckable(True)
        button.setFlat(True)
        button.setAutoFillBackground(True)
        if allow:
            style = self.STYLE_ALLOW
        else:
            style = self.STYLE_DISALLOW
        button.setStyleSheet(style)
        button.setFocusPolicy(Qt.NoFocus)

        self.mainwindow.writeAccessNeeded(button)
        self.connect(button, SIGNAL('clicked()'), partial(self.changeService, col, service, interface_network))
        self.table.setCellWidget(row, col, button)

        # with PyQt 4.4.2, table.setCellWidget(button) changes
        # the button's state (bug fixed in PyQt 4.4.4)
        button.setChecked(allow)

    # callback used when the networks are modified
    def validateNetCfg(self):
        netcfg = QNetObject.getInstance().netcfg

        previous_nets = set(self.networks) - set(self.access_cfg.custom_networks)
        new_networks = self._getNetworks(netcfg)
        new_networks = set(new_networks)

        not_in_both = previous_nets ^ new_networks
        deleted_nets = not_in_both & previous_nets
        added_nets = not_in_both & new_networks
        return True, deleted_nets, added_nets

    def validateVpnCfg(self):
        """
        always accept modifications
        """
        return True, self.getVPNConfig()

    def updateWithVpnCfg(self, new_config):
        if self.vpn_config == new_config:
            return

        # anything changed, access has to reapply the new config
        self.setModified()
        self.vpn_config = new_config

        # get old/new key
        config = self.vpn_object.getCfg()
        if self.access_cfg.custom_networks:
            old_key = self.access_cfg.custom_networks[0]
        else:
            old_key = None
        if config.enabled:
            network = config.client_network
            try:
                network = IP(network)
            except ValueError:
                # ignore invalid network: vpn check will raise an error
                return
            new_key = (OPENVPN_INTERFACE, network)
        else:
            new_key = None

        # no change? exit
        if old_key == new_key:
            return

        # create/delete vpn custom network
        if old_key:
            self.removeNetwork(old_key)
        if new_key:
            self.access_cfg.custom_networks = [new_key]
            self.appendNetwork(new_key)
        else:
            self.access_cfg.custom_networks = []
        self.setVerticalHeaders()

    def netLabel(self, interface, network):
        """
        return label for network
        """
        interface_label = interface
        network_label = str(network)
        network = IP(network)
        netcfg = QNetObject.getInstance().netcfg
        try:
            interface = netcfg.getInterfaceBySystemName(interface)
            interface_label = interface.user_label

            network = netcfg.getNet(network)
            network_label = network.displayName()
        except NoMatch:
            pass
        return tr("%s: %s") % (interface_label, network_label)

