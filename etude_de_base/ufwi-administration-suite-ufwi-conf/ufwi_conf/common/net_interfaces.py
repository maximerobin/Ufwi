# -*- coding: utf-8 -*-
"""
$Id$

PersistentID
|
|-----Interface
        |
        |-----PointToPoint
        |-----Vlan
        |-----Vlanable
                |
                |-----Ethernet
                |-----Bonding


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

from ufwi_rpcd.common.config import dict2list
from ufwi_rpcd.common.config import list2dict
from ufwi_rpcd.common.config import deserializeElement
from ufwi_rpcd.common.config import serializeElement
from ufwi_conf.common.id_store import PersistentID
from ufwi_conf.common.net_exceptions import NetCfgError
from ufwi_conf.common.net_objects_rw import NetRW, RouteRW
from ufwi_rpcd.common import tr
from ufwi_rpcd.common import is_pro

_pro = is_pro()
if _pro:
    from .net_ha import getHaIp
    from .net_ha import ha_interface_check

def valid_system_name_withMessage(name):
    if not isinstance(name, (str, unicode)):
        return False, tr("system_name should be a string (got %s)") % type(name)
    if len(name.split()) != 1:
        return False, tr("system_name should be only one word (got '%s')") % name
    return True, 'valid system name'

class Interface(PersistentID):
    """
    Generic interface, must be subclassed.
    You should probably not use this class directly.
    """
    ID_OFFSET = 0x2fffffff
    _STD_ATTRS = 'system_name user_label reserved_for_ha'.split()

    def __init__(self, **kwargs):
        PersistentID.__init__(self, **kwargs)
        system_name = kwargs.get('system_name')
        user_label = kwargs.get('user_label')
        nets = kwargs.get('nets')
        routes = kwargs.get('routes')

        if user_label is None or user_label.strip() == u'':
            user_label = system_name

        assert isinstance(system_name, (unicode, str)), tr("Found system_name to be %s") % type(system_name)
        assert isinstance(user_label, (unicode, str)), tr("Found user_label to be %s") % type(user_label)
        self.system_name = system_name
        self.user_label = user_label

        if nets is None:
            nets = set()
        self.nets = nets

        if routes is None:
            routes = set()
        self.routes = set(routes)
        self.reserved_for_ha = kwargs.get("reserved_for_ha")

    def __cmp__(self, other):
        self_active = self.freeForIp()
        other_active = other.freeForIp()
        if self_active is other_active:
            #if both interfaces have same priority:
            return cmp(self.user_label, other.user_label)
        #return higher prio
        return cmp(self_active, other_active)

    def equalsSystemWise(self, other, dont_recurse=False, ha_state=None):
        """
        ha_state : None or tuple : (self_ha_state, other_ha_state)
        """
        if not self.system_name == other.system_name:
            return False

        if not all(
            any(
                other_network.equalsSystemWise(network)
                and (
                    (not ha_state)
                    or (not _pro)
                    or (
                        getHaIp(network, ha_state[0]) == getHaIp(other_network, ha_state[1]))
                    )
                for other_network in other.nets
            )
            for network in self.nets
            ):
            return False

        if not all(
            any(
                other_route.equalsSystemWise(route)
                for other_route in other.routes
            )
            for route in self.routes
            ):
            return False

        if self.hasHA() != other.hasHA():
            return False

        if dont_recurse:
            return True

        if ha_state:
            ha_state = ha_state[::-1]
        return other.equalsSystemWise(self, dont_recurse=True, ha_state=ha_state)

    def __repr__(self):
        return "<%s>" % self.__repr()

    def __repr(self):
        return "%s unique_id=%s system_name=%r user_label=%r" % (
            self.__class__.__name__,
            self.unique_id,
            self.system_name,
            self.user_label
            )

    def addIP(self, ip_addr):
        if isinstance(ip_addr, (str, unicode)):
            ip_addr = IP(ip_addr)

        for net in self.nets:
            if net.net.overlaps(ip_addr):
                net.addIP(ip_addr)
                return True
        raise NetCfgError(tr("No network to put IP %s in.\n Networks are: %s") % \
            ((unicode(ip_addr), [net.displayName() for net in self.nets])))

    def setSystem_name(self, name):
        ok, msg = valid_system_name_withMessage(name)
        if not ok:
            raise NetCfgError(msg)
        self._system_name = name

    def getSystem_name(self):
        return self._system_name

    system_name = property(fget=getSystem_name, fset=setSystem_name)

    def freeForIp(self):
        return not self.hasHA()

    def addNet(self, net):
        self.nets.add(net)

    def delNet(self, net):
        self.nets.remove(net)

    def sync(self):
        if len(self.nets) == 0:
            self.routes.clear()

    def addRoute(self, route):
        self.routes.add(route)

    def iterNets(self):
        return iter(self.nets)

    def iterRoutes(self):
        return iter(self.routes)

    def canReserve(self):
        """
        return True if interface can be used for HA, ie if :
            - no ip config
            - no HA activated
        """
        ha_disabled = not self.reserved_for_ha
        return ha_disabled and all(len(item) == 0 for item in (self.nets, self.routes))

    def hasHA(self):
        """
        if interface is used for HA return True
        """
        return self.reserved_for_ha

    def destroy(self):
        self.deconfigure()

    def serialize(self):
        serialized = PersistentID.serialize(self)
        for attr in Interface._STD_ATTRS:
            serialized[attr] = serializeElement(getattr(self, attr))
        for attr in 'nets routes'.split():
            collection = getattr(self, attr)
            serialized[attr] = list2dict(
                (item.serialize() for item in collection)
            )
        return serialized

    def deconfigure(self):
        if self.reserved_for_ha:
            raise NetCfgError(tr(
                "Operation forbidden: this "
                "interface is configured for High Availability"
                ))
        self.clearNetworkConf()

    def clearNetworkConf(self):
        self.nets.clear()
        self.routes.clear()

    @classmethod
    def _deserialize(cls, serialized):
        kwargs = {}
        # add a default value for old conf
        if not serialized.has_key('reserved_for_ha'):
            serialized['reserved_for_ha'] = False
        for attr in Interface._STD_ATTRS:
            value = deserializeElement(serialized[attr])
            kwargs[attr] = value
        for class_name, key in {RouteRW: 'routes', NetRW: 'nets'}.iteritems():
            collection = set()
            try:
                for item in dict2list(serialized[key]):
                    collection.add(class_name.deserialize(item,))
            except KeyError:
                pass
            kwargs[key] = collection

        return kwargs

    @classmethod
    def deserialize(cls, *args):
        """
        Expects at least a serialized interface, but depending on interface type,
        more args can be needed (for instance Bonding requires a set() of ethernets)
        """
        kwargs = cls._deserialize(*args)

        return cls(**kwargs)

    def fullName(self):
        if self.user_label == self.system_name:
            return self.system_name
        return "%s (%s)" % (self.user_label, self.system_name)

    def details(self):
        yield tr("Interface type"), tr("Generic non-typed interface")

    def isValid(self):
        ok = self.isValidWithMsg()[0]
        return ok

    def isValidWithMsg(self):
        ok, msg = valid_system_name_withMessage(self.system_name)
        if not ok:
            return False, msg
        for net in self.nets:
            ok, msg = net.isValidWithMsg()
            if not ok:
                return ok, msg

        ipv4_inet_routes, ipv6_inet_routes = self.getDefaultRoutesNb()
        if ipv4_inet_routes > 1:
            return False, tr("Too many IPv4 default routes for %s") % self.fullName()
        if ipv6_inet_routes > 1:
            return False, tr("Too many IPv6 default routes for %s") % self.fullName()

        if _pro:
            ok, msg = ha_interface_check(self)
            if not ok:
                return False, msg

        return True, tr("%s is valid") % self.fullName()

    def getDefaultRoutesNb(self):
        ipv4 = 0
        ipv6 = 0
        for route in self.routes:
            if route.isDefault():
                if route.dst.version() == 4:
                    ipv4 += 1
                else:
                    ipv6 += 1

        return ipv4, ipv6

class PointToPoint(Interface):
    def details(self):
        yield tr("Interface type"), tr("Point to point")

def ip_networking(fn):
    """
    Decorator to ensure an interface used by a vlan
    or a bonding is not used for IP networking
    """
    def pre_condition(ethernet, *args, **kw):
        if not ethernet.freeForIp():
            raise NetCfgError(tr("Can not use the deactivated %s") % ethernet)
        return fn(ethernet, *args, **kw)
    return pre_condition

class Vlanable(Interface):
    def __init__(self, system_name=None, user_label=None, vlans=None, nets=None, routes=None, reserved_for_ha=False):
        Interface.__init__(self, system_name=system_name, user_label=user_label, nets=nets, routes=routes, reserved_for_ha=reserved_for_ha)

        if vlans is None:
            vlans = set()
        self.vlans = set(vlans)

    def freeForIp(self):
        return Interface.freeForIp(self)

    def freeForEnslaving(self):
        return self.canReserve()

    def canAddVlan(self):
        return True

    @ip_networking
    def addNet(self, net):
        Interface.addNet(self, net)

    @ip_networking
    def addRoute(self, route):
        Interface.addRoute(self, route)

    def addVlan(self, vlan_id, user_label):
        if not self.canAddVlan():
            raise NetCfgError(tr("Can not add a Vlan on %s") % self)
        vlan = Vlan(self.system_name, vlan_id, user_label)
        system_name = vlan.system_name
        ok, msg = valid_system_name_withMessage(system_name)
        if not ok:
            raise NetCfgError(msg)
        self.vlans.add(system_name)
        return vlan

    def serialize(self):
        serialized = Interface.serialize(self)
        serialized['vlans'] = list2dict(
            (
            vlan if isinstance(vlan, (unicode, str)) else vlan.system_name
            for vlan in self.vlans
            )
            )
        return serialized

    @classmethod
    def _deserialize(cls, serialized):
        kwargs = Interface._deserialize(serialized)
        kwargs['vlans'] = dict2list(serialized.get('vlans'))
        return kwargs

    def isValid(self, new_vlan_id=None):
        ok = self.isValidWithMsg(new_vlan_id=new_vlan_id)[0]
        return ok

    def isValidWithMsg(self, new_vlan_id=None):
        for vlan in self.vlans:
            ok, msg = valid_system_name_withMessage(vlan)
            if not ok:
                return False, msg

        ok, msg = Interface.isValidWithMsg(self)
        if not ok:
            return False, msg

        if new_vlan_id is None:
            return True, "%s is valid" % self.fullName()

        for vlan in self.vlans:
            if int(vlan.split(".")[1]) == int(new_vlan_id):
                return False, "This physical interface cannot accept a new vlan of id %i (already present)" % int(new_vlan_id)

        return True, 'valid interface'

    def equalsSystemWise(self, other, **kwargs):
        return Interface.equalsSystemWise(self, other, **kwargs)

class Ethernet(Vlanable):
    SPEEDS = 10, 100, 1000
    DUPLEX = HALF, FULL = "HALF", "FULL"
    def __init__(self,
        system_name=None,
        user_label=None,
        hard_label=None,
        vlans=None,
        nets=None,
        routes=None,
        mac_address=None,
        aggregated=None,
        eth_auto=True,
        eth_speed=None,
        eth_duplex=None,
        reserved_for_ha=False):
        Vlanable.__init__(self, system_name=system_name, user_label=user_label, vlans=vlans, nets=nets, routes=routes, reserved_for_ha=reserved_for_ha)

        if mac_address is None:
            mac_address = u''

        self.mac_address = mac_address

        if hard_label is None:
            hard_label = system_name

        assert isinstance(hard_label, (unicode, str)), tr("Found hard_label to be %s") % type(hard_label)

        self.hard_label = hard_label

        if aggregated is None:
            aggregated = False
        self.aggregated = aggregated

        self.setEthernetMode(eth_auto, eth_speed, eth_duplex)

    def equalsSystemWise(self, other, **kwargs):
        if not Vlanable.equalsSystemWise(self, other, **kwargs):
            return False

        if self.aggregated != other.aggregated:
            return False

        return True

    def setEthernetMode(self, auto, speed, duplex):
        """
        Ignoring speed and duplex if auto is True
        """
        self.eth_auto = auto
        if auto:
            self.eth_speed = None
            self.eth_duplex = None
        else:
            assert speed in Ethernet.SPEEDS, tr("Invalid speed specification: %s of type(%s)") % (speed, type(speed))
            assert duplex in Ethernet.DUPLEX, tr("Invalid duplex specification: %s of type(%s)") % (duplex, type(duplex))
            self.eth_speed = speed
            self.eth_duplex = duplex

    def canAddVlan(self):
        return not self.aggregated

    def inactive(self):
        if self.aggregated:
            raise NetCfgError(tr("Can not deactivate an aggregated interface"))
        if len(self.vlans) > 0:
            raise NetCfgError(tr("Can not deactivate an interface supporting VLANs"))
        self.deconfigure()

    def __repr(self):
        return "%s hard_label=%s" % (Interface.__repr(self), self.hard_label)

    def serialize(self):
        serialized = Vlanable.serialize(self)
        serialized['hard_label'] = self.hard_label
        serialized['aggregated'] = self.aggregated
        serialized['mac_address'] = self.mac_address
        serialized['eth_auto'] = self.eth_auto
        if not self.eth_auto:
            serialized['eth_speed'] = self.eth_speed
            serialized['eth_duplex'] = self.eth_duplex
        return serialized

    def aggregable(self):
        aggregable = (not self.vlans) and not self.aggregated and self.freeForEnslaving()
        return aggregable

    def freeForIp(self):
        return Vlanable.freeForIp(self) and (not self.aggregated)

    @classmethod
    def _deserialize(cls, serialized):
        kwargs = Vlanable._deserialize(serialized)
        for attr in """
        hard_label
        aggregated
        mac_address
        eth_speed
        eth_duplex
        """.split():
            kwargs[attr] = serialized.get(attr)

        #a default value for backward compat
        kwargs['eth_auto'] = serialized.get('eth_auto', True)
        return kwargs

    def fullName(self):
        if self.user_label == self.hard_label:
            return self.hard_label
        return "%s (%s)" % (self.user_label, self.hard_label)

    def freeForEnslaving(self):
        free = (not self.aggregated) and self.canReserve()
        return free

    def details(self):
        yield tr("Interface type"), tr("Ethernet")
        yield tr("Label on box"), self.hard_label
        if self.mac_address:
            yield tr("MAC address"), self.mac_address

    def isValid(self, **kwargs):
        ok, msg = self.isValidWithMsg(**kwargs)
        return ok

    def isValidWithMsg(self, **kwargs):
        ok, msg = Vlanable.isValidWithMsg(self, **kwargs)
        if not ok:
            return False, msg

        if not self.eth_auto:
            for val in (self.eth_speed, self.eth_duplex):
                if val is None:
                    return False, "unset speed and duplex for %s" % self.fullName()

        if self.aggregated:
            if self.nets:
                return False, "An aggregated interface (%s) cannot be used directly for networking" % self.fullName()

        return True, "valid interface %s" % self.fullName()

class Vlan(Interface):
    def __init__(self, raw_device=None, id=2, user_label=None, system_name=None, **kwargs):
        "system_name is calculated"
        #make sure it's an int
        id = int(id)

        assert raw_device is not None
        system_name = '%s.%s' % (raw_device, id)

        Interface.__init__(self, system_name=system_name, user_label=user_label, **kwargs)
        self.id = id
        if isinstance(raw_device, Interface):
            raw_device = raw_device.system_name
        self.raw_device = raw_device

    def equalsSystemWise(self, other, **kwargs):
        if not Interface.equalsSystemWise(self, other, **kwargs):
            return False

        if self.raw_device != other.raw_device:
            return False

        return True

    def serialize(self):
        serialized = Interface.serialize(self)
        id = self.id
        raw_device = self.raw_device

        if isinstance(raw_device, Interface):
            raw_device = raw_device.system_name
        serialized["id"] = id
        serialized["raw_device"] = raw_device
        return serialized

    def destroy(self):
        #removal of self.system_name from ethernets is done by netcfg_rw
        #because self doesn't know of netcfg or any ethernet address
        Interface.destroy(self)

    @classmethod
    def _deserialize(cls, serialized):
        kwargs = Interface._deserialize(serialized)
        for attr in 'id raw_device'.split():
            kwargs[attr] = serialized[attr]
        return kwargs

    def details(self):
        yield tr("Interface type"), tr("Vlan")
        yield tr("Vlan ID"), "%s" % self.id
        yield tr("Base interface"), self.raw_device

    def isValid(self):
        ok, msg = self.isValidWithMsg()
        return ok

    def isValidWithMsg(self):
        ok, msg = Interface.isValidWithMsg(self)
        if not ok:
            return False, msg

        #Vlan 0 is the untagged Vlan
        if not 0 < self.id <= 4095:
            return False, "interface %s: vlan id %s not in range 0 < 4095" % (self.id, self.fullName())
        return True, "%s is valid" % self.fullName()

class Bonding(Vlanable):
    BONDING_IDS = set()
    #Read http://linux-ip.net/html/ether-bonding.html for reference
    def __init__(self, user_label=None, ethernets=None, id=None, system_name=None, **kwargs):
#        This check must be deactivated because on startup Ethernet are restored with their 'aggregated' attribute
#        if not all(device.aggregable() for device in ethernets):
#            raise NetCfgError("Not all specified ethernet interfaces are free for aggregation")

        if id is None:
            id = 0
            while id in Bonding.BONDING_IDS:
                id += 1

        calculated_system_name = 'bond%s' % id
        if system_name is not None:
            assert calculated_system_name == system_name
        system_name = calculated_system_name

        Vlanable.__init__(self, user_label=user_label, system_name=system_name, **kwargs)

        id = int(id)
        if id in Bonding.BONDING_IDS:
            raise NetCfgError(tr("A bonding with this ID is already configured"))
        Bonding.BONDING_IDS.add(id)

        self.id = id
        self.ethernets = set()
        for device in ethernets:
            device.aggregated = True
            if device in self.ethernets:
                raise NetCfgError(tr("Same interface supplied twice"))
            self.ethernets.add(device)

    def equalsSystemWise(self, other, **kwargs):
        if not Vlanable.equalsSystemWise(self, other, **kwargs):
            return False

        aggregated = frozenset(
            (
            ethernet.system_name
            for ethernet in self.ethernets
            )
            )
        other_aggregated = frozenset(
            (
            ethernet.system_name
            for ethernet in other.ethernets
            )
            )

        if aggregated != other_aggregated:
            return False

        return True

    def getAggregatedNames(self):
        return " ".join(ethernet.fullName() for ethernet in self.ethernets)

    def destroy(self):
        for ethernet in self.ethernets:
            ethernet.aggregated = False
        Vlanable.destroy(self)
        Bonding.BONDING_IDS.remove(self.id)

    def serialize(self):
        serialized = Vlanable.serialize(self)
        serialized['id'] = self.id
        serialized['raw_devices'] = list2dict((device.system_name for device in self.ethernets))
        return serialized

    @classmethod
    def _deserialize(cls, serialized, ethernets):
        def findEthernetBySystemName(ethernets, system_name):
            for ethernet in ethernets:
                if ethernet.system_name == system_name:
                    return ethernet
            raise NetCfgError(tr("Expected ethernet interface not found: %s in %s") % (system_name, ethernets))
        kwargs = Vlanable._deserialize(serialized)
        raw_devices = serialized['raw_devices']
        kwargs['ethernets'] = tuple(
            findEthernetBySystemName(ethernets, system_name) for system_name in raw_devices.itervalues()
            )
        kwargs['id'] = serialized['id']
        return kwargs

    @classmethod
    def allowDeserialization(cls):
        Bonding._BONDING_IDS = Bonding.BONDING_IDS
        Bonding.BONDING_IDS = set()

    @classmethod
    def failedDeserialization(cls):
        Bonding.BONDING_IDS = Bonding._BONDING_IDS

    def details(self):
        yield tr("Interface type"), tr("Ethernet bonding")

        aggregated = ", ".join(
            "[%s]" % ethernet.fullName() for ethernet in self.ethernets
        )
        yield tr("Aggregating"), aggregated

