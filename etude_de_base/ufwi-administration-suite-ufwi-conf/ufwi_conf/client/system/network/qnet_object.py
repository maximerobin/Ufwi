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
from PyQt4.QtGui import QIcon, QStandardItem, QStandardItemModel

from ufwi_conf.common.netcfg_rw import deserialize
from ufwi_conf.client.qt import QConfigObject
from .network_models_names import (MODEL_NETWORKS_EXCL_HA,
    MODEL_NETWORKS_INCL_HA,
    MODEL_KNOWNNETWORKS_EXCL_HA,
    MODEL_NETWORKS_IPV4_EXCL_HA,
    MODEL_NETWORKS_IPV4_EXCL_HA_SER_PRI_SEC,
    )

class QNetObject(QConfigObject):

    def __init__(self, parent=None):
        QConfigObject.__init__(self, deserialize, 'netcfg', 'setNetCfg', parent=parent)
        self.models[MODEL_NETWORKS_EXCL_HA] = QStandardItemModel()
        self.models[MODEL_NETWORKS_INCL_HA] = QStandardItemModel()
        self.models[MODEL_KNOWNNETWORKS_EXCL_HA] = QStandardItemModel()
        self.models[MODEL_NETWORKS_IPV4_EXCL_HA] = QStandardItemModel()
        self.models[MODEL_NETWORKS_IPV4_EXCL_HA_SER_PRI_SEC] = QStandardItemModel()

        self.__net_icon = QIcon(":/icons-32/network.png")

    def __net_item(self, net):
        item = QStandardItem(self.__net_icon, net.displayName())
        item.setData(QVariant(net))
        return item

    def __interface_net(self, interface, net, net_name):
        label = "%s : %s" % (interface.fullName(), net_name)
        item = QStandardItem(self.__net_icon, label)
        bli = (interface.system_name, unicode(net))
        item.setData(QVariant(bli))
        return item

    @classmethod
    def getInitializedInstance(cls, client):
        instance = cls.getInstance()
        if not instance.has_data():
            instance.fetch_data(client)
        return instance

    def fetch_data(self, client):
        netcfg_repr = client.call("network", 'getNetconfig')
        self.netcfg = netcfg_repr

    def has_data(self):
        return self.cfg is not None

    def resetModels(self):
        for model in self.models.values():
            model.clear()

        # knownnetworks_excl_ha
        for interface, network, net_name in self.cfg.iterKnownNetworks(name=True):
            interface_net_item = self.__interface_net(interface, network, net_name)
            self.models[MODEL_KNOWNNETWORKS_EXCL_HA].appendRow(interface_net_item)

        # networks_ipv4_excl_ha
        for network in self.cfg.iterNetworks(include_ha=False, version=4):
            net_item = self.__net_item(network)
            self.models[MODEL_NETWORKS_IPV4_EXCL_HA].appendRow(net_item)
            if (
                network.service_ip_addrs
                and network.primary_ip_addrs
                and network.secondary_ip_addrs
               ):
                net_item = self.__net_item(network)
                model = self.models[MODEL_NETWORKS_IPV4_EXCL_HA_SER_PRI_SEC]
                model.appendRow(net_item)

        # networks_excl_ha
        # networks_incl_ha
        for interface in self.cfg.iterNetworkables():
            for net in interface.nets:

                if not interface.hasHA():
                    net_item = self.__net_item(net)
                    self.models[MODEL_NETWORKS_EXCL_HA].appendRow(net_item)

                net_item = self.__net_item(net)
                self.models[MODEL_NETWORKS_INCL_HA].appendRow(net_item)

        #General reset, to reset views
        for model in self.models.values():
            model.reset()

