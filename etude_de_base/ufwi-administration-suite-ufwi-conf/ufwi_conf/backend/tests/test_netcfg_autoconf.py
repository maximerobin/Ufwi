
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

import logging
from StringIO import StringIO

#from ufwi_conf.backend.netcfg_autoconf import NetCfgAutoConf
from ..netcfg_autoconf import NetCfgAutoConf

class TestNetCfg():

    def setup_class(self):
        logging.basicConfig(level=logging.DEBUG,)

    def setup_method(self, method):
        self.netcfg = NetCfgAutoConf()

    def test_discover_normal(self):
        #
        #lo: must be ignored
        #eth0: added to netcfg.ethernets
        #truc0: must be ignored
        sample_ip_addr = StringIO("""\
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 16436 qdisc noqueue state UNKNOWN
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
    inet6 ::1/128 scope host
       valid_lft forever preferred_lft forever
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP qlen 1000
    link/ether 00:16:76:ab:79:ed brd ff:ff:ff:ff:ff:ff
    inet 192.168.0.1/24 brd 192.168.0.255 scope global eth0
    inet6 2a01:7d2:7d2:7d2:216:76ff:feab:79ed/64 scope global dynamic
       valid_lft 86266sec preferred_lft 86266sec
    inet6 fe80::216:76ff:feab:79ed/64 scope link
       valid_lft forever preferred_lft forever
3: truc0: <POINTOPOINT,MULTICAST,NOARP,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UNKNOWN qlen 100
    link/[65534]
    inet 10.8.0.66 peer 10.8.0.65/32 scope global tun0
""")

        self.netcfg.discover(ip_flow=sample_ip_addr)

        assert len(self.netcfg.ethernets) == 1
        ethernet = self.netcfg.ethernets.pop()
        assert len(ethernet.nets) == 2
        for net in ethernet.nets:
            #label is IPy.IP.strNormal()
            if net.label == '2a01:7d2:7d2:7d2::/64':
                assert len(net.ip_addrs) == 1
            elif net.label == '192.168.0.0/24':
                assert len(net.ip_addrs) == 1
            else:
                assert False, "something wrong with network %s" % net.label
        assert self.netcfg.isValid()

    def test_discover_pointopoint(self):

        #
        #lo: must be ignored
        #eth0: added to netcfg.ethernets
        #truc0: must be ignored
        sample_ip_addr = StringIO("""\
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 16436 qdisc noqueue state UNKNOWN
link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
inet 127.0.0.1/8 scope host lo
inet6 ::1/128 scope host
   valid_lft forever preferred_lft forever
2: eth1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UNKNOWN qlen 1000
link/ether 08:00:27:7f:ae:08 brd ff:ff:ff:ff:ff:ff
inet 10.0.159.17/24 brd 10.0.159.255 scope global eth1
inet6 fe80::a00:27ff:fe7f:ae08/64 scope link
   valid_lft forever preferred_lft forever
88: edw-multisite: <POINTOPOINT,MULTICAST,NOARP,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UNKNOWN qlen 100
link/[65534]
inet 10.254.0.6 peer 10.254.0.5/32 scope global edw-multisite
""")
        self.netcfg.discover(ip_flow=sample_ip_addr)
        assert len(self.netcfg.ethernets) == 1
        ethernet = self.netcfg.ethernets.pop()

        assert len(self.netcfg.pointtopoints) == 1
        assert self.netcfg.isValid()



