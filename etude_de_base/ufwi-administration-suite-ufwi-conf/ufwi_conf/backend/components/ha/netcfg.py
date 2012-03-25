#coding: utf-8
"""
Copyright (C) 2010-2011 EdenWall Technologies

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

import IPy

from ufwi_conf.common.net_base import any_ha, active_ha
from ufwi_conf.common.net_ha import getHaIp

class HaNetCfg(object):
    """Adapter for NetCfg class"""
    def __init__(self, netcfg):
        self.netcfg = netcfg

    def ipResources(self):
        """Return list of all IP resources/service IPs"""
        text = u""
        for interface in self.netcfg.iterInterfaces():
            interface = HaInterface(interface)
            for ip_def in interface.iterIpResources():
                text += u"    %s \\\n" % ip_def
        return text

    def ipNotResources(self, ha_type):
        """Return list of all primary/secondary IPs"""
        text = u""
        for interface in self.netcfg.iterInterfaces():
            interface = HaInterface(interface)
            for ip_def in interface.iterIpNotResources(ha_type):
                text += u"    %s \\\n" % ip_def
        return text

    def routeResources(self):
        """resources is True: return list of all route resources
           else return list of all route which are not resources"""
        # only resource/service routes
        filter_route = lambda net: ( len(net.primary_ip_addrs) == 0 and
            len(net.secondary_ip_addrs) == 0 )
        return self.getRoutes(filter_route)

    def routeNotResources(self, ha_type):
        # only not resource/service routes
        if active_ha(ha_type):

            def filter_route(net):
                return net.primary_ip_addrs or net.secondary_ip_addrs

            return self.getRoutes(filter_route)

        def accept_routes(net):
            return  True

        return self.getRoutes(accept_routes)

    def getRoutes(self, filter_route):
        text = u""
        for route in self.iterRoutes(filter_route):
            net = str(IPy.IP(route.dst.ip))
            mask = str(route.dst.netmask())
            gateway = str(route.router)

            if len(net) > 1:
                fmt = u"    iproute::%s::%s::net::%s \\\n"
                text += fmt % (net, gateway, mask)
            else:
                fmt = u"    iproute::%s::%s::host \\\n"
                text += fmt % (net, gateway)

        return text

    def iterRoutes(self, filter_route):
        """
        return routes which are resources if resources is True,
        else return routes which are not resources
        """
        for interface in self.netcfg.iterInterfaces():
            for route in interface.iterRoutes():
                for net in interface.iterNets():
                    if net.net.overlaps(route.router) and filter_route(net):
                        yield route

    def saveNotHaResources(self, ha_type):
        """
        save what primary or secondary IPs we have. heartbeat script IPaddr2EW
        will use this data in order to prevent deletion of these IPs
        Format one ip by line : "    IPaddr2EW::IP/netmask/iface \"
                                "    IPaddr2EW::192.168.1.1/24/eth0 \"
        """
        with open("/var/lib/ufwi_rpcd/ufwi_conf/ha/IPaddresses","w") as handle:
            handle.write(self.ipNotResources(ha_type))

        """
        save what primary or secondary routes we have. heartbeat script iproute
        will use this data in order to prevent deletion of these routes
        Format one ip by line : "    iproute::network::gateway::[net|host]::mask \"
               a default route: "    iproute::0.0.0.0::192.168.1.50::net::0.0.0.0 \"
        """
        with open("/var/lib/ufwi_rpcd/ufwi_conf/ha/Routes","w") as handle:
            handle.write(self.routeNotResources(ha_type))


class HaInterface(object):
    """Adapter for Interface class"""
    def __init__(self, interface):
        self.interface = interface

    def iterIpResources(self):
        """iter over all service IPs"""
        for net in self.interface.iterNets():
            net = HaNet(net)
            for ip_def in net.iterIpResources(self.interface.system_name):
                yield ip_def

    def iterIpNotResources(self, ha_type):
        """iter over all service IPs"""
        for net in self.interface.iterNets():
            net = HaNet(net)
            for ip_def in net.iterIpNotResources(self.interface.system_name, ha_type):
                yield ip_def

class HaNet(object):
    """Adapter for Net class"""
    HA_CF_FORMAT = u"IPaddr2EW::%s/%i/%s"
    def __init__(self, net):
        self.net = net

    def formatIpResource(self, ip, iface):
        """return service ip formatted as an ha resource"""
        prefix = self.net.net.prefixlen()
        return HaNet.HA_CF_FORMAT % (unicode(ip), prefix, iface)

    def iterIpResources(self, iface):
        """
        Return service ips formatted as ha resources
        iface parameter must be interface_system_name
        """
        for ip in self.net.service_ip_addrs:
            yield self.formatIpResource(ip, iface)

    def iterIpNotResources(self, iface, ha_type):
        """
        Return primary or secondary ips formatted as ***ha resources***
        iface parameter must be interface_system_name
        """
        if not any_ha(ha_type):
            return

        for ip in getHaIp(self.net, ha_type):
            yield self.formatIpResource(ip, iface)

