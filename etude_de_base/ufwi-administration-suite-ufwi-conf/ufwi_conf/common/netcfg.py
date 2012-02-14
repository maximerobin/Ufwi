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

from re import compile

from ufwi_rpcd.common.abstract_cfg import DatastructureIncompatible
from ufwi_rpcd.common.config import dict2list
from ufwi_rpcd.common.tools import deprecationWarning
from ufwi_conf.common.net_exceptions import NoMatch
from ufwi_conf.common.net_interfaces import Ethernet, Bonding, Vlan, Interface, Vlanable

"""
Network config utility.

Deserialization:
__module__.deserializeNetCfg(): NetCfg


UML Object scheme (see reading help at the bottom):

                                   +---------------+              +------------+
                                   | Iface         |              | Net        |
                                   +---------------+ 1          * +------------+
 +-------------+                   | +user_label   |---+--------->| +net       |
 | NetCfg      |                   | +name         |   |     nets | +ip_addrs  |
 +-------------+ 1               * | +hard_label   |   |iterNets()| +label     |
 | +discover() +------------------>| +vlans        |   |          +------------+
 | +serialize()|        interfaces | +bonding_over |   |
 +-------------+  iterInterfaces() |  ifaces       |   |          +----------+
                                   | +aggregated_  |   |        * | Route    |
                                   |  in_bond_iface|   +--------->+----------+
                                   | +addIP()      |       routes | +iface   |
                                   +---------------+  iterRoutes()| +router  |
                                Vlan, Ethernet, Bonding           | +dst     |
                                                                  +----------+
Reading help:
Rectangles are classes.
1 or * represent cardinalities (1 NetCfg for [0..+infty] interfaces)
Arrows mean visibility (NetCfg sees Iface ; Iface does not see NetCfg).
Names near arrows are the attribute name (Iface are stored in NetCfg.interfaces).
"""

DATASTRUCTURE_VERSION = 1

_VLAN_HARD_LABEL_PARSER = compile(r'(?P<base>.*)\[(?P<vlanid>.*)]')

def _checkSerialVersion(serialized):
    datastructure_version = serialized.get('DATASTRUCTURE_VERSION')
    if datastructure_version != DATASTRUCTURE_VERSION:
        raise DatastructureIncompatible('received incompatible netcfg object, '
        'expected %r, got %r' % (DATASTRUCTURE_VERSION, datastructure_version))

def _deprecated(fn):
    def deprecated(*args, **kw):
        deprecationWarning("WARNING: deprecated call to %s" % fn.__name__, 3)
        return fn(*args, **kw)
    return deprecated


def _match_ip_version(version, ip):
    if version not in (4, 6):
        return True
    return ip.version() == version

def _set_if_none(value):
    if value is None:
        return set()
    return value

class NetCfg(object):
    def __init__(self, ethernets=None, vlans=None, bondings=None, pointtopoints=None):
        self.ethernets = _set_if_none(ethernets)
        self.vlans = _set_if_none(vlans)
        self.bondings = _set_if_none(bondings)
        self.pointtopoints = _set_if_none(pointtopoints)

    def __len__(self):
        return len(self.ethernets | self.vlans | self.bondings)

    def iterInterfaces(self, reverse=False):
        """
        Iterate over interfaces in the following order: ethernets, bondings, vlans, ptp

        Use case: 'ifup'ing interfaces in this order is very useful.
        'ifdown'ing them in the reverse order is a pretty feature as well.
        """
        ordered_containers = [self.ethernets, self.bondings, self.vlans, self.pointtopoints]
        if reverse:
            ordered_containers.reverse()
        for container in ordered_containers:
            for interface in container:
                yield interface

    #For compatibility
    @_deprecated
    def iterIfaces(self, *args, **kwargs):
        return self.iterInterfaces(*args, **kwargs)

    def iterVlanables(self):
        return iter(self.ethernets|self.bondings)

    def iterPointToPoints(self):
        return iter(self.pointtopoints)

    def iterVlans(self):
        return iter(self.vlans)

    def iterEthernets(self):
        return iter(self.ethernets)

    def iterBondings(self):
        return iter(self.bondings)

    def iterNetworkables(self):
        for interface in self.iterInterfaces():
            if ( not interface.hasHA() ) \
                and isinstance(interface, Vlan) \
                or interface.freeForIp():

                yield interface

    def iterAggregables(self):
        """
        buffers first 2 interfaces
        """
        first = None
        bufferring = True

        for interface in self.iterEthernets():
            if interface.aggregable():
                if first is None:
                    first = interface
                    continue
                if bufferring:
                    yield first
                    bufferring = False
                yield interface

    def iterNetworks(self, include_ha=True, version=-1):
        for interface in self.iterNetworkables():
            if interface.reserved_for_ha and (not include_ha):
                continue
            for network in interface.iterNets():
                if _match_ip_version(version, network.net):
                    yield network

    def iterKnownNetworks(self, name=False, version=-1):
        """
        This yields pairs of (interface, network)

        * interface is an Interface object
        * network is a IPy.IP object that might be a host (ipv4/32 or ipv6/128).
        HA network is actively skipped

        If name=True, the network name is appended if available, or unicode(IPy.IP)

        If version is 4 or 6, only provides networks of this IP version
        """
        for interface in self.iterNetworkables():
            if interface.hasHA():
                continue
            for network in interface.iterNets():
                if _match_ip_version(version, network.net):
                    if name:
                        yield interface, network.net, network.displayName()
                    else:
                        yield interface, network.net
            for route in interface.iterRoutes():
                if _match_ip_version(version, route.dst):
                    if name:
                        yield interface, route.dst, unicode(route.dst)
                    else:
                        yield interface, route.dst

    def iterRoutes(self, default_only=False):
        for interface in self.iterNetworkables():
            for route in interface.routes:
                if (not default_only) or route.isDefault():
                    yield route

    def iterAddresses(self):
        for net in self.iterNetworks():
            for addr in net.ip_addrs:
                yield addr

    def iterInterfaceChildrenNames(self, interface, showparent=True):
        if showparent:
            yield interface.system_name

        if isinstance(interface, Vlanable):
            for vlan in interface.vlans:
                yield vlan

        if isinstance(interface, Ethernet):
            try:
                bonding = self.getBondingByAggregatedEthernet(interface)
            except NoMatch:
                pass
            else:
                yield bonding.system_name
                for vlan in bonding.vlans:
                    yield vlan

    def hasIP(self, ip):
        return ip in self.iterAddresses()

    def getRouteInterface(self, route):
        for interface in self.iterNetworkables():
            for iface_route in interface.routes:
                if iface_route == route:
                    return interface
        raise NoMatch("This route is unknown")

    def getInterfaceForIp(self, ip):
        """
         expects IPy.IP
        """
        for interface in self.iterNetworkables():
            for net in interface.iterNets():
                if net.net.overlaps(ip):
                    return interface
        raise NoMatch("No default gateway")

    def getNetForIp(self, ip):
        """
         expects IPy.IP
        """
        for interface in self.iterNetworkables():
            for net in interface.iterNets():
                if net.net.overlaps(ip):
                    return net
        return None

    def getInterfaceByUserLabel(self, user_label):
        for interface in self.iterInterfaces():
            if interface.user_label == user_label:
                return interface
        raise NoMatch('Interface with hard_label "%s" not found' % user_label)

    def getInterfaceForNet(self, net):
        for interface in self.iterInterfaces():
            if net in interface.nets:
                return interface
        raise NoMatch("This network is unknown")

    def getInterfaceForRoute(self, route):
        for interface in self.iterInterfaces():
            if route in interface.routes:
                return interface
        raise NoMatch("Unknown route")

    def getBondingByAggregatedEthernet(self, ethernet):
        for bonding in self.bondings:
            if ethernet in bonding.ethernets:
                return bonding
        raise NoMatch("No bonding aggregates '%s'" % ethernet.fullName())

    def getIfaceByHardLabel(self, hard_label):
        match = _VLAN_HARD_LABEL_PARSER.match(hard_label)
        if match is not None:
            #VLAN
            base = match.group('base')
            vlanid = match.group('vlanid')
            try:
                base_interface = self.getIfaceByHardLabel(base)
            except NoMatch:
                raise NoMatch(
                    "Supposed to find a base interface with hard_label "
                    "'%s' supporting a vlan '%s'" % (base, vlanid)
                )
            vlan_system_name = '.'.join([base_interface.system_name, vlanid])
            if not vlan_system_name in base_interface.vlans:
                raise NoMatch(
                "Interface '%s has no vlan '%s'" %
                (base_interface.fullName(), vlan_system_name)
                )
            return self.getInterfaceBySystemName(vlan_system_name)

        if '+' in hard_label:
            #BONDING
            bases = hard_label.split('+')
            bonding = None
            for base in bases:
                ethernet = self.getIfaceByHardLabel(base)
                found_bonding = self.getBondingByAggregatedEthernet(ethernet)
                if bonding is None:
                    bonding = found_bonding
                else:
                    if bonding is not found_bonding:
                        #Setting the error condition
                        bonding = None
                        break
            if bonding is None:
                raise NoMatch(
                "No Bonding aggregating '%s'" % (' '.join(bases))
                )
            return bonding

        #ethernet
        for interface in self.iterEthernets():
            if interface.hard_label == hard_label:
                return interface
        raise NoMatch('Interface with hard_label "%s" not found' % hard_label)

    def getHardLabel(self, interface):
        """
        does not necessarily give a sensible name for the use
        """
        if isinstance(interface, Ethernet):
            return interface.hard_label
        if isinstance(interface, Vlan):
            raw_device = self.getInterfaceBySystemName(interface.raw_device)
            base_part = self.getHardLabel(raw_device)

            return "%s[%s]" % (base_part, interface.id)
        if isinstance(interface, Bonding):
            hard_labels = [
                ethernet.hard_label for ethernet in interface.ethernets
            ]
            hard_labels.sort()
            return "+".join(hard_labels)

        assert False, "%s %s" % (interface, type(interface))
        return interface

    def getInterfaceBySystemName(self, name):
        for interface in self.iterInterfaces():
            if interface.system_name == name:
                return interface
        raise NoMatch('Interface with name "%s" not found in %s' % (name, unicode(tuple(self.iterInterfaces()))))

    #For compatibility
    getIfaceByName = getInterfaceBySystemName

    def getNet(self, net):
        """
        Finds the object for the IPy network you provide
        """
        for obj in self.iterNetworks():
            if obj.net == net:
                return obj
        raise NoMatch('Network with address %s not found' % net)

    def getNetByLabel(self, label):
        for net in self.iterNetworks():
            if net.label == label:
                return net
        raise NoMatch('Network with label %s not found' % label)

    def getNetByUniqueID(self, unique_id):
        for net in self.iterNetworks():
            if net.unique_id == unique_id:
                return net
        raise NoMatch('Network with id %s not found' % unique_id)

    def getInterfaceByUniqueID(self, unique_id):
        for interface in self.iterInterfaces():
            if interface.unique_id == unique_id:
                result =  interface
                assert isinstance(interface, Interface), "%s %s" % (type(interface), interface)
                return result
        raise NoMatch('Interface with id %s not found' % unique_id)

#    def findRoutes(self, dst = None, router = None):
#        for route in self.iterRoutes():
#            if (dst is None or route.dst == dst) \
#            and (router is None or route.router == router):
#                yield route
#

    def getDefaultGateway(self, ip_version):
        """
        Get the default gateway of the specified IP version.
        Return (address, interface) where address is an IPy.IP
        object and interface an Iface object.
        """
        for route in self.iterRoutes():
            if route.dst.version() != ip_version:
                continue
            if route.isDefault():
                return (route.router, self.getInterfaceForIp(route.router))
        raise NoMatch('Default gateway for IP version %s not found' % ip_version)

    def isValid(self):
        ok, msg = self.isValidWithMsg()
        del msg
        return ok

    def _bondings_sanity(self):
        used_ethernets = set()
        for bonding in self.bondings:
            if used_ethernets & bonding.ethernets:
                return False, "Some ethernets are used in more than one bonding."

            used_ethernets |= bonding.ethernets

        for ethernet in self.ethernets:
            if ethernet.aggregated:
                if not ethernet in used_ethernets:
                    return False, "Ethernet interface %s is marked as aggregated but is used nowhere" % ethernet.fullName()
        return True, "ok"

    def _no_duplicate_net(self):
        nets_ips = set()
        for interface in self.iterInterfaces():
            for net in interface.iterNets():
                if net.net in nets_ips:
                    return False, "Duplicate network definition (second occurrence at %s - %s/%s)." % (
                        interface
                    )

        nets = tuple(
            net.net for net in self.iterNetworks()
            )
        _nets = []
        for net in nets:
            if _nets and any(
                net.overlaps(other_net)
                for other_net in _nets
                ):
                return False, "Network %s overlaps another network, and you cannot do that" % str(net)
            _nets.append(net)
        return True, "ok"

    def isValidWithMsg(self):
        ipv4_inet_routes = 0
        ipv6_inet_routes = 0

        for interface in self.iterInterfaces():
            ok, msg = interface.isValidWithMsg()
            if not ok:
                return ok, msg
            _ipv4, _ipv6 = interface.getDefaultRoutesNb()
            ipv4_inet_routes += _ipv4
            ipv6_inet_routes += _ipv6

        if ipv4_inet_routes > 1:
            return False, "Too many ipv4 default routes."
        if ipv6_inet_routes > 1:
            return False, "Too many ipv6 default routes."

        ok, msg = self._bondings_sanity()
        if not ok:
            return False, msg

        ok, msg = self._no_duplicate_net()
        if not ok:
            return False, msg

        return True, "Valid network configuration"
###

def deserializeNetCfg(serialized_cfg, cls=NetCfg, parent=None):
    _checkSerialVersion(serialized_cfg)

    vlans = set()

    for serialized_vlan in dict2list(serialized_cfg.get('vlans')):
        vlans.add(Vlan.deserialize(serialized_vlan))

    ethernets = set()
    for serialized_ethernet in dict2list(serialized_cfg.get('ethernets')):
        ethernets.add(Ethernet.deserialize(serialized_ethernet))

    bondings = set()
    Bonding.allowDeserialization()
    try:
        for serialized_bonding in dict2list(serialized_cfg.get('bondings')):
            bondings.add(Bonding.deserialize(serialized_bonding, ethernets))
    except:
        Bonding.failedDeserialization()
        raise

    if parent is None:
        return cls(ethernets=ethernets, vlans=vlans, bondings=bondings)
    return cls(ethernets=ethernets, vlans=vlans, bondings=bondings, parent=parent)


def deserialize(serialized_cfg):
    return deserializeNetCfg(serialized_cfg, NetCfg)
