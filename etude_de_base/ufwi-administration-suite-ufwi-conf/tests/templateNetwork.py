#coding: utf-8
"""
Test of the network configuration.

Copyright (C) 2009-2011 EdenWall Technologies
Written by Julien Miotte <jmiotte AT edenwall.com>
$Id$
"""

#from ldap import initialize, SCOPE_SUBTREE
from __future__ import with_statement
from copy import deepcopy
from templateTest import Test
from os import makedirs
from os.path import isdir

class templateNetwork(Test):
    """ 
        Test of the network configuration.
        - Check that /etc/network/interfaces has changed
        - Check that /etc/network/interfaces is correctly written
        - Check the output of "ip a show" on the interface set
    """
    test_network = {}
    @classmethod
    def setup_class(cls):
        """
            This method is called once when the class is first instanciated. It
            sets up the testing conditions, while saving the current configuration.
        """
        Test.setup_class()

        cls.test_path = cls.results_path+cls.date+"/TestNetwork/"
        if not isdir(cls.test_path):
            makedirs(cls.test_path)

        with open("/sys/class/net/eth0/operstate","r") as handle:
            eth0_state = handle.readlines()

        cls.firstMD5_interfaces = cls.md5sum("/etc/network/interfaces")

        serialized = cls.client.call('network','getNetconfig')
        cls.orig = deepcopy(serialized)

        # Configure the network according to the input script
        serialized = cls.configure_network(serialized)

        # Save and apply the configuration
        cls.takeNuconfWriteRole()
        cls.client.call("network", "setNetconfig", serialized, "none")
        cls.apply_nuconf()

        # Let's check that eth0 isn't affected by our changes
        with open("/sys/class/net/eth0/operstate","r") as handle:
            state = handle.readlines()
            assert eth0_state == state, "eth0 changes when it shouldn't"

    def test_interfaces_has_changed(self):
        """
            Check that /etc/network/interfaces has changed
        """
        second_md5 = self.md5sum("/etc/network/interfaces")

        assert second_md5 != "","/etc/network/interfaces has not been created"
        error = "/etc/network/interfaces has not been changed"
        assert second_md5 != self.firstMD5_interfaces, error

    def test_interfaces_is_correctly_written(self):
        """
            Check that /etc/network/interfaces is correctly written
        """
        filename = "/etc/network/interfaces"
        expected = tuple(self.test_network["service"])
        self.correctly_written(filename, expected)

    def test_ip_address(self):
        """
            Check the output of "ip a show" on the interface set
        """
        command = "ip a show primary dev %s" % self.test_network["iface"]
        expected = tuple(self.test_network["service"])
        self.output_check(command, expected)

    @classmethod
    def teardown_class(cls):
        """
            This method is called once when all tests have been done.
            It restores the saved configuration.
        """
        with open("/sys/class/net/eth0/operstate","r") as handle:
            eth0_state = handle.readlines()

        cls.client.call('network', 'setNetconfig', cls.orig, 'pas de message')
        cls.apply_nuconf()

        # Let's check that eth0 isn't affected by our changes
        with open("/sys/class/net/eth0/operstate","r") as handle:
            state = handle.readlines()
            assert eth0_state == state, "eth0 changes when it shouldn't"

        Test.teardown_class()
