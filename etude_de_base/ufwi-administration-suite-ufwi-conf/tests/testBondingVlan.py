#coding: utf-8
"""
Test of bonding + VLAN configuration (checking conf & ip)

Copyright (C) 2009-2011 EdenWall Technologies
Written by Julien Miotte <jmiotte AT edenwall.com>
$Id:$
"""
from nuconf.common.netcfg_rw import deserialize
from nuconf.common.net_objects_rw import NetRW, RouteRW
from copy import deepcopy
from IPy import IP
from templateTest import Test
from os import makedirs
from os.path import isdir

class TestBondingVlan(Test):
    """ Test of bonding + VLAN configuration :
        - check that when we add a route on the bonding interface, the vlans
          aren't teared down.
        - check that when we add an ID on the bonding interface, the vlans are
          aren't teared down.
    """

    bond_sys_name = ""

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
        eth1 = netcfg.getInterfaceBySystemName('eth1')
        eth2 = netcfg.getInterfaceBySystemName('eth2')

        netcfg_bondings = set(netcfg.bondings)
        for bonding in netcfg_bondings:
            if eth1 in bonding.ethernets:
                netcfg.removeInterface(bonding)
                break
        netcfg.removeInterface(eth1)

        netcfg_bondings = set(netcfg.bondings)
        for bonding in netcfg_bondings:
            if eth2 in bonding.ethernets:
                netcfg.removeInterface(bonding)
                break
        netcfg.removeInterface(eth2)

        bond0 = netcfg.createBonding('bond0', set((eth1, eth2)))

        # Give an IPv4 configuration to our bonding
#        net = NetRW(
#                "James",
#                IP("192.168.242.0/24"),
#                service_ip_addrs=set(IP("192.168.242.1"),)
#                )
#
#        bond0.addNet(net)

        # Let's add a few vlans
        cls.vlans = []
        for id in range(1, 5):
            myvlan = netcfg.createVlan(bond0, "vlan%s" % id, id)
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
                        serialized, "created a bonding")
        cls.apply_nuconf()

        # Fetch the system name of the bonding we've just created
        netconfig = cls.client.call("network", "getNetconfig")
        netcfg = deserialize(netconfig)
        bond_interface = netcfg.getInterfaceByUserLabel('bond0')
        cls.bond_sys_name = bond_interface.getSystem_name()

    def test_vlans_are_up(self):
        """
            Since we gave an IP address to our VLANs, they should be
            administratively up.
        """
        command = "ip l show dev %s"
        expected = (",UP,",)
        for vlan in self.vlans:
            self.output_check(command % vlan, expected)

    def test_vlans_up_when_adding_ip(self):
        """
            Check that the vlans are not teared down when we add an ip to the
            bonding.
        """
        netcfg = deepcopy(self.test_netcfg)
        net = NetRW(
                "James",
                IP("192.168.222.0/24"),
                service_ip_addrs=set(IP("192.168.222.1"),)
                )

        bond_interface = netcfg.getInterfaceByUserLabel('bond0')
        bond_interface.addNet(net)

        self._apply_test_conf_and_check(netcfg)

    def test_vlans_down_when_adding_route(self):
        """
            Check that the vlans are not teared down when we add a route to the
            bonding.
        """
        netcfg = deepcopy(self.test_netcfg)
        my_route = RouteRW(IP("192.168.111.0/24"),
                           IP("192.168.222.1")
                  )
        bond_interface = netcfg.getInterfaceByUserLabel('bond0')
        bond_interface.addRoute(my_route)

        self._apply_test_conf_and_check(netcfg)

    def _apply_test_conf_and_check(self, netcfg):
        """
            Apply a configuration for the aim of a test, and check the state of
            the vlans.
        """
        # Let's apply the new configuration
        serialized = netcfg.serialize()
        self.takeNuconfWriteRole()
        self.client.call("network", "setNetconfig",
                        serialized, "created a bonding")
        self.apply_nuconf()

        command = "ip l"
        expected = tuple(vlan for vlan in self.vlans)
        for vlan in self.vlans:
            self.output_check(command, expected)

        self.test_vlans_are_up()

    @classmethod
    def teardown_class(cls):
        """
            This method is called once when all tests have been done.
            It restores the saved configuration.
        """
#        cls.client.call('network', 'setNetconfig', cls.orig, 'pas de message')
#        cls.apply_nuconf()

        Test.teardown_class()
