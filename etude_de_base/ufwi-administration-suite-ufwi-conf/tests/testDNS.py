#coding: utf-8
"""
Testing the DNS configuration.

Copyright (C) 2009-2011 EdenWall Technologies
Written by Julien Miotte <jmiotte AT edenwall.com>
$Id$
"""

from copy import deepcopy
from templateTest import Test
from os import makedirs
from os.path import isdir
from datetime import datetime

class TestDNS(Test):
    """ 
        Testing the DNS configuration :
        - Check that /etc/bind/named.conf.options has changed.
        - Check that /etc/bind/named.conf.options is correctly written.
        - Check that /etc/resolv.conf points to 127.0.0.1
        - Check that we can query the DNS server via localhost (through dig)
    """
    REQUIRE_COMPONENTS = ('resolv', 'bind')

    @classmethod
    def setup_class(cls):
        """
            This method is called once when the class is first instanciated. It
            sets up the testing conditions, while saving the current configuration.
        """
        Test.setup_class()

        cls.test_path = cls.results_path+cls.date+"/TestDNS/"
        if not isdir(cls.test_path):
            makedirs(cls.test_path)

        cls.firstMD5_resolv_conf = cls.md5sum("/etc/bind/named.conf.options")

        resolv_config = cls.client.call('resolv', 'getResolvConfig')
        cls.orig = deepcopy(resolv_config)

        # Test DNS
        resolv_config['nameserver1'] = cls.DNS_server['ip']
        resolv_config['nameserver2'] = ''

        # Apply configuration
        cls.takeNuconfWriteRole()

        print datetime.now(), "applying dumbconfig"
        dumbconfig = {'domain': 'foobar.com',
                      'nameserver1': '192.168.254.253',
                      'nameserver2': '192.168.254.254'}
        cls.client.call('resolv', 'setResolvConfig',
                        dumbconfig, 'resolv dumbconfig')
        cls.apply_nuconf()
        print datetime.now(), "applied dumbconfig"

        print datetime.now(), "applying testconfig"
        cls.client.call('resolv', 'setResolvConfig',
                        resolv_config, 'pas de message')
        cls.apply_nuconf()
        print datetime.now(), "applied testconfig"

    def _named_conf_has_changed(self):
        """
            Check that /etc/bind/named.conf.options has changed.
        """
        second_md5 = self.md5sum("/etc/bind/named.conf.options")

        assert second_md5 != "", "/etc/bind/named.conf has not been created"
        error = "/etc/bind/named.conf.options has not been changed"
        assert self.firstMD5_resolv_conf != second_md5, error

    def _named_conf_has_been_written(self):
        """
            Check that /etc/bind/named.conf.options is correctly written.
        """
        filename = "/etc/bind/named.conf.options"
        expected = ("forwarders.*%s" % self.DNS_server['ip'], )
        self.correctly_written(filename, expected)

    def _resolv_conf(self):
        """
            Check that /etc/resolv.conf points to 127.0.0.1
        """
        filename = "/etc/resolv.conf"
        expected = ("nameserver 127.0.0.1", )
        self.correctly_written(filename, expected)

    def _dig_localhost(self):
        """
            Check that we can query the DNS server via localhost (through dig)
        """
        command = "dig hebus.inl.fr @localhost"
        expected = ("ANSWER SECTION", )
        self.output_check(command, expected)

    @classmethod
    def teardown_class(cls):
        """
            This method is called once when all tests have been done.
            It restores the saved configuration.
        """
        cls.client.call('resolv', 'setResolvConfig', cls.orig, 'test message')
        cls.apply_nuconf()

        Test.teardown_class()

    def test_generative(self):
        """
            Automated generation of tests
        """
        yield self._resolv_conf
        yield self._dig_localhost
        yield self._named_conf_has_changed
        yield self._named_conf_has_been_written

if __name__ == "__main__":
    choice = raw_input("Calling this file directly will cause application of\n"
                       "the test configuration without reverting it.\n"
                       "You should call it with py.test.\nContinue anyway ? "
                       "[yN] : ")
    if 'y' in choice.strip():
        one_shot = TestDNS()
        one_shot.setup_class()
