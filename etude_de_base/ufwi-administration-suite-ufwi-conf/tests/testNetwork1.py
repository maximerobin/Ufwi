#coding: utf-8
"""
Simple eth configuration test (implementing templateNetwork)

Copyright (C) 2009-2011 EdenWall Technologies
Written by Julien Miotte <jmiotte AT edenwall.com>
$Id: testNetwork.py 14889 2009-11-26 18:37:40Z jmiotte $
"""

#from ldap import initialize, SCOPE_SUBTREE
from __future__ import with_statement
from nuconf.common.netcfg_rw import deserialize
from nuconf.common.net_objects_rw import NetRW
from IPy import IP
from templateNetwork import templateNetwork

class TestNetwork1(templateNetwork):
    """
        Test case : simple eth interface
    """
    test_network = {"name"      : "test",
                    "iface"     : "eth1",
                    "network"   : IP("192.168.72.0/24"),
                    "service"   : set(IP("192.168.72.1"),),
                    "primary"   : set(IP("192.168.72.11"),),
                    "secondary" : set(IP("192.168.72.12"),)}

    @classmethod
    def configure_network(cls, serialized):
        """
            Custom network configuration
        """
        netcfg = deserialize(serialized)

        eth1 = netcfg.getInterfaceBySystemName(cls.test_network["iface"])
        netcfg_bondings = set(netcfg.bondings)
        for bonding in netcfg_bondings:
            if eth1 in bonding.ethernets:
                netcfg.removeInterface(bonding)
                break
        netcfg.removeInterface(eth1)

        net = NetRW(
                    cls.test_network["name"],
                    cls.test_network["network"],
                    primary_ip_addrs = cls.test_network["primary"],
                    secondary_ip_addrs = cls.test_network["secondary"],
                    service_ip_addrs = cls.test_network["service"]
                    )
        eth1.addNet(net)

        return netcfg.serialize()
