#coding: utf-8
"""
Test of bonding configuration.

Copyright (C) 2009-2011 EdenWall Technologies
Written by Julien Miotte <jmiotte AT edenwall.com>
$Id$
"""

#from ldap import initialize, SCOPE_SUBTREE
from nuconf.common.netcfg_rw import deserialize
from nuconf.common.net_objects_rw import NetRW
from copy import deepcopy
from IPy import IP
from templateTest import Test
from os import makedirs
from os.path import isdir

class TestBonding(Test):
    """ 
        We had a bonding (bond0) on two interfaces (eth1 and eth2), and then
        check that :
        - /etc/network/interfaces is correctly written
        - the output of ip a show {bond0, eth1, eth2} is correct
    """

    bond_sys_name = ""

    @classmethod
    def setup_class(cls):
        """
            This method is called once when the class is first instanciated. It
            sets up the testing conditions, while saving the current configuration.
        """
        Test.setup_class()

        cls.test_path = cls.results_path+cls.date+"/TestBonding/"
        if not isdir(cls.test_path):
            makedirs(cls.test_path)

        # Get /etc/network/interfaces md5sum for comparison
        cls.firstMD5_interfaces = cls.md5sum("/etc/network/interfaces")

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
        net = NetRW(
                "James",
                IP("192.168.242.0/24"),
                service_ip_addrs=set(IP("192.168.242.1"),)
                )

        bond0.addNet(net)
        serialized = netcfg.serialize()

        # Let's apply the new configuration
        cls.takeNuconfWriteRole()
        cls.client.call("network", "setNetconfig",
                        serialized, "created a bonding")
        cls.apply_nuconf()

        # Fetch the system name of the bonding we've just created
        netconfig = cls.client.call("network", "getNetconfig")
        netcfg = deserialize(netconfig)
        bond_interface = netcfg.getInterfaceByUserLabel('bond0')
        cls.bond_sys_name = bond_interface.getSystem_name()

    def test_interfaces_is_correctly_written(self):
        """
            Check that /etc/network/interfaces is correctly written.
        """
        second_md5 = self.md5sum("/etc/network/interfaces")
        assert second_md5 != ""," /etc/network/interfaces has not been created"
        error = "/etc/network/interfaces has not changed"
        assert second_md5 != self.firstMD5_interfaces, error

        filename = "/etc/network/interfaces"
        expected = ("up /sbin/ifenslave "+self.bond_sys_name+" eth2",
                    "up /sbin/ifenslave "+self.bond_sys_name+" eth1",
                    "address 192.168.242.1")
        self.correctly_written(filename, expected)

    def test_ip_address_bond0(self):
        """
            Check the output of "ip a show primary dev bond0".
        """
        command = "ip a show primary dev %s" % self.bond_sys_name
        expected = "inet 192.168.242.1/24 brd 192.168.242.255 scope global %s"
        expected_tuple = (expected % self.bond_sys_name,)
        self.output_check(command, expected_tuple)

    def test_ip_address_eth1(self):
        """
            Check the output of "ip a show primary dev eth1".
        """
        command = "ip a show primary dev eth1"
        expected = (self.bond_sys_name,)
        self.output_check(command, expected)

    def test_ip_address_eth2(self):
        """
            Check the output of "ip a show primary dev eth2".
        """
        command = "ip a show primary dev eth2"
        expected = (self.bond_sys_name,)
        self.output_check(command, expected)

    @classmethod
    def teardown_class(cls):
        """
            This method is called once when all tests have been done.
            It restores the saved configuration.
        """
        cls.client.call('network', 'setNetconfig', cls.orig, 'pas de message')
        cls.apply_nuconf()

        Test.teardown_class()
