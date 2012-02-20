#coding: utf-8
"""
Template file for tests of routed networks configuration

Copyright (C) 2009-2011 EdenWall Technologies
Written by Julien Miotte <jmiotte AT edenwall.com>
$Id$
"""

from nuconf.common.netcfg_rw import deserialize
from nuconf.common.net_objects_rw import NetRW, RouteRW
from copy import deepcopy
from IPy import IP
from templateTest import Test
from os import makedirs
from os.path import isdir

class templateRoutedNetworks(Test):
    """ 
        Test of routed networks configuration
        - check that /etc/network/interfaces is modified
        - check that it contains the correct information
        - check that the route is active with 'ip route'
    """
    network_test = {}
    @classmethod
    def setup_class(cls):
        """
            This method is called once when the class is first instanciated. It
            sets up the testing conditions, while saving the current configuration.
        """
        Test.setup_class()

        cls.test_path = cls.results_path+cls.date+"/"+cls.__name__+"/"
        if not isdir(cls.test_path):
            makedirs(cls.test_path)

        # We save the configuration to restore it later
        serialized = cls.client.call('network','getNetconfig')
        cls.orig = deepcopy(serialized)

        for i in serialized['ethernets']:
            # Remove every route
            if serialized['ethernets'][i]['routes'] != {}:
                serialized['ethernets'][i]['routes'] = {}

        netcfg = deserialize(serialized)

        eth1 = netcfg.getInterfaceBySystemName('eth1')
        netcfg_bondings = set(netcfg.bondings)
        for bonding in netcfg_bondings:
            if eth1 in bonding.ethernets:
                netcfg.removeInterface(bonding)
                break

        netcfg.removeInterface(eth1)
        net = NetRW(
                    "Test",
                    IP(cls.network_test["local_net"]),
                    service_ip_addrs=set(IP(cls.network_test["local_ip"]))
                    )
        eth1.addNet(net)
        my_route = RouteRW(IP(cls.network_test["routed_net"]),
                          IP(cls.network_test["gateway"])
                  )
        eth1.addRoute(my_route)

        # In order to check that /etc/network/interfaces does change :
        cls.firstMD5_interfaces = cls.md5sum("/etc/network/interfaces")

        # We apply the network configuration
        serialized = netcfg.serialize()
        cls.takeNuconfWriteRole()
        cls.client.call('network', 'setNetconfig',
                        serialized, 'pas de message')
        cls.apply_nuconf()

    def test_intefaces_has_changed(self):
        """
            Verification que /etc/network/interfaces est ecrit
        """
        second_md5 = self.md5sum("/etc/network/interfaces")
        error = "/etc/network/interfaces has not changed"

        assert self.firstMD5_interfaces != second_md5, error

    def test_interfaces_is_correctly_written(self):
        """
            Verification que /etc/network/interfaces est bien ecrit (avec les bonnes infos)
        """
        filename = "/etc/network/interfaces"
        expected = (self.network_test["should_have_interfaces"],)
        self.correctly_written(filename, expected)

    def test_ip_route(self):
        """
            Check that the route is currently used by the system
        """
        command = "ip route"
        expected = (self.network_test["should_have_ip_route"],)
        self.output_check(command, expected)

    @classmethod
    def teardown_class(cls):
        """
            This method is called once when all tests have been done.
            It restores the saved configuration.
        """
        # Retour a la configuration initiale
        cls.client.call('network', 'setNetconfig', cls.orig, 'pas de message')
        cls.apply_nuconf()

        Test.teardown_class()

# Please create a new class if you want to test a new route configuration.
# Please commit your new route configurations.
