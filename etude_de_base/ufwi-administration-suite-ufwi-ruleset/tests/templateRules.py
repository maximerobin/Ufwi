#coding: utf-8
"""
Copyright (C) 2009-2011 EdenWall Technologies
Written by Julien Miotte <jmiotte AT edenwall.com>
$Id$
"""

from ldap import initialize, SCOPE_SUBTREE
from ufwi_conf.common.netcfg_rw import deserialize
from ufwi_conf.common.net_objects_rw import NetRW
from copy import deepcopy
from ufwi_rpcd.client.error import RpcdError
from IPy import IP
import os
from templateTest import Test
from os import makedirs
from os.path import isdir
from pprint import pprint

class templateRules(Test):
    """ Test of routed networks configuration
        - check that /etc/network/interfaces is modified
        - check that it contains the correct information
        - check that the route is active with 'ip route'
    """
    ruleV4 = {}
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
        serialized = cls.client.call('network', 'getNetconfig')
        cls.orig = deepcopy(serialized)

        # Let's tune the netconf to match our needs
        netcfg = deserialize(serialized)

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

        net1 = NetRW(
                    "Test1",
                    IP("192.168.16.0/24"),
                    service_ip_addrs=set(IP("192.168.16.1"))
                    )

        net2 = NetRW(
                    "Test2",
                    IP("192.168.17.0/24"),
                    service_ip_addrs=set(IP("192.168.17.1"))
                    )

        eth1.addNet(net1)
        eth2.addNet(net2)

        serialized = netcfg.serialize()

        cls.takeNuconfWriteRole()
        cls.client.call("network", "setNetconfig", serialized, "none")
        cls.apply_ufwi_conf()

        cls.should_have_resources = '<interface id=\"eth1\" name=\"eth1\">\n' \
            '         <network address=\"192.168.16.0/24\" id=\"Test1\" />\n' \
            '      </interface>\n' \
            '      <interface id=\"eth2\" name=\"eth2\">\n' \
            '         <network address=\"192.168.17.0/24\" id=\"Test2\" />\n' \
            '      </interface>'

        # We save the last applied ruleset name
        cls.origRuleset = None
        production_rules = cls.client.call('ufwi_ruleset', 'productionRules')
        if production_rules.has_key('ruleset'):
            cls.origRuleset = cls.client.call('ufwi_ruleset',
                                            'productionRules')['ruleset']

        # If the ruleset used exists, we delete it
        for ruleset in cls.client.call('ufwi_ruleset', 'rulesetList', 'ruleset'):
            if cls.ruleV4['name'] in ruleset:
                cls.client.call('ufwi_ruleset',
                                'rulesetDelete',
                                'ruleset',cls.ruleV4['name'])
                break

        # We create a new ruleset and name it
        cls.client.call('ufwi_ruleset', 'rulesetCreate', 'ruleset', '')

        # We create a user group
        user_group = {'group': '9000', 'id': 'tests'}
        cls.client.call('ufwi_ruleset',
                        'objectCreate',
                        'user_groups',
                        user_group,
                        False)

        # We add the rule
        cls.client.call('ufwi_ruleset',
                        'ruleCreate',
                        'acls-ipv4',
                        cls.ruleV4['rule'])

        # Save and apply the rule
        cls.client.call('ufwi_ruleset', 'rulesetSaveAs', cls.ruleV4['name'])
        cls.client.call('ufwi_ruleset', 'applyRules', 'True', 'True')
        cls.client.call('ufwi_ruleset', 'rulesetClose')

    def test_xml_is_correctly_written(self):
        """
            Check that the ruleset was saved in a xml file
            Check that the xml file is correctly writtent
        """
        filename = "/var/lib/ufwi_ruleset3/rulesets/%s.xml" % self.ruleV4['name']
        error = "The ruleset isn't saved in a xml file"
        assert os.path.isfile(filename), error

        filename = "/var/lib/ufwi_ruleset3/rulesets/"+self.ruleV4['name']+".xml"
        expected = (self.should_have_resources, self.ruleV4['xml_file'])
        self.correctly_written(filename, expected)

    def test_iptables_is_correct(self):
        """
            If the rule is not authentifying, check that it is applied
        """
        command = "iptables -nvL ETH1-ETH2"
        expected = (self.ruleV4['iptables'],)
        self.output_check(command, expected)

    def test_LDAP_is_correct(self):
        """
            Check that the ruleset has been stored in ldap
        """
        if self.ruleV4['rule']['user_groups'] != []:
            config = self.client.call('ufwi_ruleset', 'getConfig')['ldap']
            basedn = config['basedn']
            uri = 'ldap://%s:%s' % (config['host'], config['port'])

            cursor = initialize(uri)
            cursor.simple_bind_s(config['username'], config['password'])
            result = cursor.search(basedn,
                                   SCOPE_SUBTREE,
                                  '(objectClass=NuAccessControlList)')

            all_results = []
            while True:
                result_type, data = cursor.result(result, 0)
                if data == []:
                    break
                _cn, attr = data[0]
                print result_type, _cn
                all_results.append(attr)

            print "We should have :"
            pprint(self.ruleV4['dump_ldap'])
            print "We get :"
            pprint(all_results)

            error = "check your ldap directory"
            assert all_results == self.ruleV4['dump_ldap'], error

    @classmethod
    def teardown_class(cls):
        """
            This method is called once when all tests have been done.
            It restores the saved configuration.
        """
        # If the ruleset used exists, we delete it
        for ruleset in cls.client.call('ufwi_ruleset', 'rulesetList', 'ruleset'):
            if cls.ruleV4['name'] in ruleset:
                cls.client.call('ufwi_ruleset',
                                'rulesetDelete',
                                'ruleset', cls.ruleV4['name'])
                break

        # If there was any ruleset open, now we close it
        try:
            cls.client.call('ufwi_ruleset', 'rulesetClose')
        except RpcdError:
            pass

        # If the previous ruleset still exists, we restore it
        if cls.origRuleset:
            for ruleset in cls.client.call('ufwi_ruleset', 'rulesetList', 'ruleset'):
                if 'origRuleset' in ruleset:
                    cls.client.call('ufwi_ruleset',
                                    'rulesetOpen', 'ruleset', cls.origRuleset)
                    cls.client.call('ufwi_ruleset', 'applyRules', 'True', 'True')
                    cls.client.call('ufwi_ruleset', 'rulesetClose')
                    break

        # Retour a la configuration initiale
        cls.client.call('network', 'setNetconfig', cls.orig, 'pas de message')
        cls.apply_ufwi_conf()

        Test.teardown_class()

# Please create a new class in new file if you want to test new acls.
# Please commit your new acls.
