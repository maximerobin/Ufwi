
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

from __future__ import with_statement
from ufwi_conf.common.netcfg import NetCfg
from ufwi_conf.common.netcfg import DATASTRUCTURE_VERSION
from ufwi_conf.common.netcfg import deserializeNetCfg
from ufwi_conf.common.net_exceptions import NoMatch
from ufwi_conf.common.net_exceptions import NetCfgError
from ufwi_conf.common.net_interfaces import Ethernet
from ufwi_conf.common.net_interfaces import Vlanable
from ufwi_conf.common.net_interfaces import Vlan
from ufwi_conf.common.net_interfaces import Bonding
from ufwi_rpcd.common.config import list2dict
from ufwi_rpcd.common import is_pro

_pro = is_pro()
if _pro:
    from ufwi_conf.common.ha_cfg import _deconfigureHA

class NetCfgRW(NetCfg):

    def serialize(self):
        serialized = {
            'ethernets': list2dict([ethernet.serialize() for ethernet in self.iterEthernets()]),
            'vlans': list2dict([vlan.serialize() for vlan in self.iterVlans()]),
            'bondings': list2dict([bonding.serialize() for bonding in self.iterBondings()]),
            'DATASTRUCTURE_VERSION': DATASTRUCTURE_VERSION
            }
        return serialized

    def canCreateVlan(self):
        iterator = self.iterVlanables()
        try:
            iterator.next()
            return True
        except StopIteration:
            return False

    def canCreateBonding(self):
        for item in self.iterAggregables():
            del item
            return True
        return False

    def canCreateNetwork(self):
        for interface in self.iterNetworkables():
            return True

    def canCreateIface(self):
        return self.canCreateVlan() or self.canCreateBonding()

    def activateIface(self, hard_label, user_label):
        iface = self.getIfaceByHardLabel(hard_label)
        iface.active = True
        if user_label != iface.user_label:
            self._renameInterface(hard_label, user_label)

    def _renameInterface(self, interface, new_label):

        if new_label == "":
            #Actually erasing label
            if isinstance(interface, Ethernet):
                new_label = interface.hard_label
            else:
                new_label = interface.system_name
            self._renameIface(interface, new_label)
            return

        #Else: checking for conflicts
        try:
            other_interface = self.getInterfacefaceByUserLabel(new_label)
        except NoMatch:
            self._renameIface(interface, new_label)
            return
        if interface != other_interface:
            raise NetCfgError(
                "User label already taken: %s (for iface %s)" % (new_label, other_interface.fullName())
                )
        self._renameIface(interface, new_label)

    def getInterfacefaceByUserLabel(self, user_label):
        for interface in self.iterInterfaces():
            if interface.user_label == user_label:
                return interface
        raise NoMatch("Interface not found")

    def _renameIface(self, iface, user_label):
        iface.user_label = user_label

    def createBonding(self, user_label, ethernets):
        if len(ethernets) < 2:
            raise NetCfgError("At least 2 interfaces are needed to create a bonding.")
        for bonding in self.bondings:
            for ethernet in ethernets:
                if ethernet in bonding.ethernets:
                    raise NetCfgError(
                        "Cannot use %s to create a bonding, "
                        "it is already used in %s." %
                        (ethernet.fullName(), bonding.fullName())
                        )
        bonding = Bonding(user_label, ethernets)
        self.bondings.add(bonding)
        return bonding

    def createVlan(self, raw_device, user_label, vlan_id):
        """
        raw_device: a Vlanable
        """
        if isinstance(raw_device, (unicode, str)):
            raw_device = self.getInterfaceBySystemName(raw_device)
        vlan = raw_device.addVlan(vlan_id, user_label)
        self.vlans.add(vlan)
        return vlan

    def moveVlan(self, vlan, new_raw_device):
        current_raw_device = vlan.raw_device
        if isinstance(current_raw_device, (unicode, str)):
            current_raw_device = self.getInterfaceBySystemName(current_raw_device)
        if isinstance(new_raw_device, (unicode, str)):
            new_raw_device = self.getInterfaceBySystemName(new_raw_device)

        new_vlan_system_name = "%s.%s" % (new_raw_device.system_name, vlan.id)

        if vlan.system_name not in current_raw_device.vlans:
            raise NetCfgError("not registered in original raw_device")
        current_raw_device.vlans.remove(vlan.system_name)

        new_raw_device.vlans.add(new_vlan_system_name)
        vlan.system_name = new_vlan_system_name
        vlan.raw_device = new_raw_device.system_name

    def _additional_removals(self, interface):
        additional_removals = set()
        if isinstance(interface, Vlanable):
            for vlan in interface.vlans:
                vlan_interface = self.getInterfaceBySystemName(vlan)
                additional_removals.add(vlan_interface)

        elif isinstance(interface, Ethernet):
            for bonding in self.bondings:
                if interface in bonding.ethernets:
                    additional_removals.add(bonding)
                    break
        return additional_removals

    def removeInterface(self, interface):
        if _pro:
            if interface.hasHA():
                _deconfigureHA(interface)

        for other_interface in self._additional_removals(interface):
            self.removeInterface(other_interface)

        interface.clearNetworkConf()

        if isinstance(interface, Ethernet):
            interface.aggregated = False

        elif isinstance(interface, Vlan):
            self.vlans.discard(interface)
            raw_device = self.getInterfaceBySystemName(interface.raw_device)
            raw_device.vlans.discard(interface.system_name)

        else:
            assert isinstance(interface, Bonding), "unexpected interface type %s" % type(interface)
            self.bondings.discard(interface)
            for ethernet in interface.ethernets:
                ethernet.aggregated = False

def deserialize(serialized_cfg, cls=NetCfgRW, parent=None):
    result = deserializeNetCfg(serialized_cfg, cls, parent=parent)
    ok, msg = result.isValidWithMsg()
    if not ok:
        raise NetCfgError(msg)
    return result

