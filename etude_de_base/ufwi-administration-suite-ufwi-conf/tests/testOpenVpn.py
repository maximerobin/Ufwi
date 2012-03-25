#coding: utf-8
"""
OpenVpn configuration test (only applying valid and invalid)

Copyright (C) 2010-2011 EdenWall Technologies
Written by Pierre-Louis Bonicoli <bonicoli AT edenwall.com>
"""

from __future__ import with_statement
from templateTest import Test
from nucentral.client.error import NuCentralError
from nucentral.common.error import NUCONF
from nuconf.common.error import NUCONF_OPENVPN
from nuconf.common.openvpn_cfg import OPENVPN_INVALID_CONFIGURATION, OpenVpnConf

class TestOpenVpn(Test):
    """
        In this test we try to apply valid and invalid configurations and check
        nucentral reacts coherently.
    """

    PKI_TEST = {
        "name"      : u"ovpn",
        "org unit"  : u"testou",
        "org"       : u"testorg",
        "loc"       : u"labas",
        "state"     : u"ici",
        "country"   : u"fr"
    }

    CERT_TEST = {
        "type"      : u"server",
        'pki'       : PKI_TEST["name"],
        "cname"     : u"ovpncert",
        "email"     : u"root@edw",
        "organization_unit"  : u"testou",
        "location"  : u"labas",
        "state"     : u"ici",
        "country"   : u"fr",
        'force'     : True,
    }

    VALID_CONF = {
        'DATASTRUCTURE_VERSION': 4,
         '__type__': 'nuconf.common.openvpn_cfg.OpenVpnConf',
         'ca': '',
         'cert': '',
         'client_network': '10.100.8.0/22',
         'crl': '',
         'disable_crl': False,
         'enabled': True,
         'key': '',
         'manual_pushed_routes': {'0': {'IP': '192.168.30.0/24', '__type__': 'IP'},
                                  '__type__': 'tuple'},
         'nupki_cert': CERT_TEST['cname'],
         'nupki_pki': PKI_TEST['name'],
         'port': '1194',
         'protocol': 'udp',
         'redirect': False,
         'server': '109.0.21.2',
         'use_nupki': True
    }

    # redirect disable but manual_pushed_routes is empty
    INVALID_CONF = {
        'DATASTRUCTURE_VERSION': 4,
         '__type__': 'nuconf.common.openvpn_cfg.OpenVpnConf',
         'ca': '',
         'cert': '',
         'client_network': '10.100.8.0/22',
         'crl': '',
         'disable_crl': False,
         'enabled': True,
         'key': '',
         'manual_pushed_routes': {'__type__': 'tuple'},
         'nupki_cert': 'test',
         'nupki_pki': 'test',
         'port': '1194',
         'protocol': 'udp',
         'redirect': False,
         'server': '109.0.21.2',
         'use_nupki': True
    }

    @classmethod
    def setup_class(cls):
        """
            This method is called once when the class is first instanciated. It
            sets up the testing conditions, while saving the current configuration.
        """
        Test.setup_class()

        # Save the original configuration
        cls.orig = cls.client.call('openvpn', 'getOpenVpnConfig')
        conf = OpenVpnConf.deserialize(cls.orig)
        is_valid, error = conf.isValidWithMsg()
        assert is_valid, "original configuration is invalid ('%s : %s') !" % (error, cls.orig)

        # Create a pki
        cls.client.call('nupki', 'createPKI',
            cls.PKI_TEST["name"],
            cls.PKI_TEST["org unit"],
            cls.PKI_TEST["org"],
            cls.PKI_TEST["loc"],
            cls.PKI_TEST["state"],
            cls.PKI_TEST["country"], 1826)

        cls.client.call('nupki', 'createCertificate', cls.CERT_TEST)

    def test_save_conf1(self):
        """Save and apply a valid configuration"""
        self.takeNuconfWriteRole()
        self.client.call("openvpn", "setOpenVpnConfig", self.VALID_CONF,
            "test_save_conf1")
        self.apply_nuconf()

        status = self.client.call("status", "getStatus")[0]
        assert status['openvpn'] == 'RUNNING', 'nucentral says openvpn is not running'

    def test_save_conf2(self):
        """Save and apply a invalid configuration"""
        self.takeNuconfWriteRole()
        try:
            self.client.call("openvpn", "setOpenVpnConfig", self.INVALID_CONF,
                "test_save_conf2")
        except NuCentralError, error:
            if error.code != (NUCONF, NUCONF_OPENVPN, OPENVPN_INVALID_CONFIGURATION):
                assert True, ("Call to openvpn.setOpenVpnConfig must failed with InvalidConfiguration exception"
                    ", but '%s' found" % error.type)
        else:
            assert True, "Call to openvpn.setOpenVpnConfig must failed"

    @classmethod
    def teardown_class(cls):
        """
            This method is called once when all tests have been done.
            It restores the saved configuration.
        """
        # Clean after our tests
        cls.takeNuconfWriteRole()
        cls.client.call('openvpn', 'setOpenVpnConfig', cls.orig,
            'test openvpn - restore orginal configuration')
        cls.apply_nuconf()

        cls.client.call('nupki', 'deletePKI', cls.PKI_TEST['name'])

        Test.teardown_class()

