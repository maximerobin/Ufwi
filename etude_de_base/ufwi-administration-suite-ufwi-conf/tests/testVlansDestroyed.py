#coding: utf-8
"""
Checking https://edw.inl.fr/trac/ticket/1876.

Copyright (C) 2009-2011 EdenWall Technologies
Written by Julien Miotte <jmiotte AT edenwall.com>
$Id:$
"""

from os import makedirs
from os.path import isdir
from copy import deepcopy
from templateTest import Test
from nuconf.common.netcfg_rw import deserialize
from nuconf.common.net_objects_rw import NetRW
from IPy import IP

class TestVlansDestroyed(Test):
    """
    Problem:
     - Read https://edw.inl.fr/trac/ticket/1876

     - in the config:
       - take a virgin ethernet, give it an IP configuration.
       - add 2 vlans to that ethernet, with IP configuration.
     - apply
     - see how everything works
     - in the config:
       - delete your ethernet (your vlans should be gone in the config)
     - apply
     - see how everything works NOT: one VLAN could not be deleted by the system.
    """

    @classmethod
    def setup_class(cls):
        """
            This method is called once when the class is first instanciated. It
            sets up the testing conditions, while saving the current configuration.
        """
        Test.setup_class()

        cls.test_path = cls.results_path+cls.date+"/TestBondingVlan/"
        if not isdir(cls.test_path):
            makedirs(cls.test_path)

        # Get and save our netconfig
        netconfig = cls.client.call("network","getNetconfig")
        cls.orig = deepcopy(netconfig)
        netcfg = deserialize(netconfig)

        # Let's configure for our test
        cls.eth1 = netcfg.getInterfaceBySystemName('eth1')

        netcfg_bondings = set(netcfg.bondings)
        for bonding in netcfg_bondings:
            if cls.eth1 in bonding.ethernets:
                netcfg.removeInterface(bonding)
                break
        netcfg.removeInterface(cls.eth1)

        # Let's add a few vlans
        cls.vlans = []
        for id in range(1,2):
            myvlan = netcfg.createVlan(cls.eth1, "vlan%s" % id, id)
            net = NetRW(
                    "my_net%s" % id,
                    IP("192.168.10%s.0/24" % id),
                    service_ip_addrs=set(IP("192.168.10%s.1" % id),)
                    )
            myvlan.addNet(net)
            my_syst_name = myvlan.getSystem_name()
            cls.vlans.append(my_syst_name)

        # We're gonna reuse this config in our tests
        cls.test_netcfg = netcfg

        # Let's apply the new configuration
        serialized = netcfg.serialize()
        cls.takeNuconfWriteRole()
        cls.client.call("network", "setNetconfig",
                        serialized, "added 2 vlans")
        cls.apply_nuconf()

        # Fetch the system name of the bonding we've just created
        netconfig = cls.client.call("network", "getNetconfig")
        netcfg = deserialize(netconfig)

    def deconfigure_eth1(self):
        self.test_netcfg.removeInterface(self.eth1)
        serialized = self.test_netcfg.serialize()
        self.client.call("network", "setNetconfig",
                         serialized, "added 2 vlans")
        self.apply_nuconf()

    def test_all(self):
        self.output_check("ip a", tuple(self.vlans), should_find=True)
        self.deconfigure_eth1()
        self.output_check("ip a", tuple(self.vlans), should_find=False)

    @classmethod
    def teardown_class(cls):
        """
            This method is called once when all tests have been done.
            It restores the saved configuration.
        """
        cls.client.call('network', 'setNetconfig', cls.orig, 'pas de message')
        cls.apply_nuconf()

        Test.teardown_class()
