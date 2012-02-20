#coding: utf-8
"""
Template test file for DHCP tests (nucentral, checking the configuration)

Copyright (C) 2009-2011 EdenWall Technologies
Written by Julien Miotte <jmiotte AT edenwall.com>
$Id:$
"""

from __future__ import with_statement
from copy import deepcopy
from templateTest import Test
from os import makedirs
from os.path import isdir

from IPy import IP
from nuconf.common.dhcpcfg import deserialize as deserialize_dhcp
from nuconf.common.dhcpcfg import DHCPRange
from nuconf.common.dhcpcfg import UNSET
from nuconf.common.netcfg_rw import deserialize as deserialize_net

from commonNetwork import configure_simple_ethernet

class templateDHCP(Test):
    """
        Test of the DHCP configuration feature
    """

    test_dhcp = {}
    configure_network = classmethod(configure_simple_ethernet)

    @classmethod
    def setup_class(cls):
        """
            This method is called once when the class is first instanciated. It
            sets up the testing conditions, while saving the current configuration.
        """
        Test.setup_class()

        cls.test_path = cls.results_path+cls.date+"/TestDHCP/"
        if not isdir(cls.test_path):
            makedirs(cls.test_path)

        # Configure the network according to the input script
        serialized = cls.client.call('network', 'getNetconfig')
        cls.net_orig = deepcopy(serialized)

        iface = (cls.test_network["iface"],)
        (serialized, net) = cls.configure_network(serialized,
                                                  iface,
                                                  cls.test_network)

        # Save the original configuration
        orig = cls.client.call('dhcp', 'getDhcpConfig')
        cls.dhcp_orig = deepcopy(orig)

        # Prepare to change the configuration
        netcfg = deserialize_net(serialized)
        dhcpcfg = deserialize_dhcp(orig, netcfg)

        # Do we configure the DNS server ?
        dns_server = None
        if cls.configure_dns:
            dns_server = IP(cls.test_dhcp['dns_server'])

        # Do we configure the router ?
        router = None
        if cls.configure_router:
            router = IP(cls.test_dhcp['router'])

        dhcp_range = DHCPRange(
                            router,
                            dns_server,
                            IP(cls.test_dhcp['start']),
                            IP(cls.test_dhcp['end']),
                            net
                     )

        assert dhcp_range.isValid()

        dhcpcfg.ranges.add(dhcp_range)
        dhcpcfg.enabled = True

        # Save and apply the configuration
        cls.takeNuconfWriteRole()
        cls.client.call("network", "setNetconfig", netcfg.serialize(),
                        "Add a network for dhcp testing purposes")
        cls.client.call("dhcp", "setDhcpConfig", dhcpcfg.serialize(),
                        "Add a dhcp range for testing purposes")
        cls.apply_nuconf()

    def test_nucentral_says_its_running(self):
        """
            Trust nucentral and check its answer
        """
        status = self.client.call("status", "getStatus")[0]
        assert status["dhcp"] == "RUNNING", "nucentral says it's not running"

    def test_dhcpd_conf_is_correctly_written(self):
        """
            Check that /etc/dhcp3/dhcpd.conf is correctly written
        """
        filename = "/etc/dhcp3/dhcpd.conf"

        net = IP(self.test_dhcp['net_label'])
        subnet = str(net.net())
        netmask = str(net.strNetmask())
        start = self.test_dhcp['start']
        end = self.test_dhcp['end']
        dns_server = self.test_dhcp['dns_server']
        router = self.test_dhcp['router']

        IPV4 = "((25[0-5]|2[0-4]\d|1\d\d|[1-9]\d|\d)\.){3}(25[0-5]|2[0-4]\d|1\d\d|[1-9]\d|\d)"

        _sp = lambda stmt: "\s*%s\s*\n" % stmt
        expected = _sp("subnet %s netmask %s {" % (subnet, netmask))
        # domain-name-servers here only if dns_server configured
        if dns_server != UNSET and self.configure_dns:
            expected += _sp('option domain-name-servers %s;' % dns_server)

        if router != UNSET and self.configure_router:
            expected += _sp('option routers %s;' % router)
        else:
            expected += _sp('option routers %s;' % IPV4)

        expected += _sp("pool {")
        expected += _sp("range %s %s;" % (start, end))
        expected += _sp('}')
        expected += _sp('}')

        self.correctly_written(filename, (expected,))

    @classmethod
    def teardown_class(cls):
        """
            This method is called once when all tests have been done.
            It restores the saved configuration.
        """
        # Clean after our tests
        cls.client.call('network',
                        'setNetconfig',
                        cls.net_orig,
                        'pas de message')
        cls.client.call('dhcp',
                        'setDhcpConfig',
                        cls.dhcp_orig,
                        "Add a dhcp range for testing purposes")
        cls.apply_nuconf()

        Test.teardown_class()
