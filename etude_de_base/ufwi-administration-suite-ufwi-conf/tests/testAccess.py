#coding: utf-8
"""
Test of the access module (calling it, checking its return)

Copyright (C) 2009-2011 EdenWall Technologies
Written by Julien Miotte <jmiotte AT edenwall.com>
$Id$
"""

from os import makedirs
from os.path import isdir
from templateTest import Test

SERVICES = ['bind', 'dhcp', 'exim', 'ntp', 'nucentral_access', 'openvpn',
            'ping_access','squid', 'snmpd', 'site2site', 'auth_cert']

class TestAccess(Test):
    """ Test of the access module :
        - check that we have all the services

        todo:
        - check that it uses the right networks
        - check that iptables is correct after setting a new access configuration
    """
    @classmethod
    def setup_class(cls):
        """
            This method is called once when the class is first instanciated. It
            sets up the testing conditions, while saving the current configuration.
        """
        Test.setup_class()

        cls.test_path = cls.results_path+cls.date+"/TestAccess/"
        if not isdir(cls.test_path):
            makedirs(cls.test_path)

    def test_access_has_all_services(self):
        """
            Check that we have all services are present in access.getServices.
        """
        result = self.client.call("access","getServices")
        difference = set(SERVICES).difference(set(result))
        error = "access misses component: %s" % str(difference)

        assert difference == set([]), error

    @classmethod
    def teardown_class(cls):
        """
            This method is called once when all tests have been done.
            It restores the saved configuration.
        """
        Test.teardown_class()
