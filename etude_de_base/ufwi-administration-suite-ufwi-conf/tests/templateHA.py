#coding: utf-8
"""
Copyright (C) 2009-2011 EdenWall Technologies
Written by Julien Miotte <jmiotte AT edenwall.com>
$Id: testNetwork.py 14889 2009-11-26 18:37:40Z jmiotte $
"""

from __future__ import with_statement
from time import sleep
from nuconf.common.netcfg_rw import deserialize
from copy import deepcopy
import subprocess
from templateTest import Test
from os import makedirs
from shutil import copy
from os.path import isdir

def postMortem(method):
    def new_method(self,*args,**kwargs):
        try:
            return method(self,*args,**kwargs)
        except:
            if method.__name__ == "test_interfaces_is_correctly_written":
                copy("/etc/network/interfaces",self.test_path)
                expected = ("192.168.72.1",)
                self.autotestsSays(self.test_path+"interfaces",expected)

            elif method.__name__ == "test_ip_address":
                subprocess.Popen("ip a show primary dev eth1 >> "+self.test_path+"/ip_a_show_eth1",
                                 shell=True)
                expected = ("192.168.72.1",)
                self.autotestsSays(self.test_path+"interfaces",expected)

            raise
    return new_method

class templateHA(Test):
    """ Test d'application d'une configuration HA
        - check that the setup is replicated
            - when it is prior to the HA configuration & join
            - when it has occured after the HA configuration & join
    """
    @classmethod
    def setup_class(cls):
        Test.setup_class()

        cls.test_path = cls.results_path+cls.date+"/TestHA/"
        if not isdir(cls.test_path):
            makedirs(cls.test_path)

        #################################### Configuration of the secondary
        # Check that the EW has a license
        cls.checkAndUploadLicense(Test.cluster_ha["secondary"])

        # Connect to the other nucentral
        cls.other_client = cls.createClient(host=Test.cluster_ha["secondary"])

        # Let's synchronize our watches
        cls.client.call('ntp',
                        'setNtpConfig',
                        {
                            'ntpservers': u'172.16.0.1',
                            'isFrozen': False
                        },
                        u'message')
        cls.client.call('ntp', 'syncTime')

        # Let's configure the HA on the secondary
        cls.other_client.call('ha',
                              'configureHA',
                              cls.secondary_ha_configuration,
                              u'message')

        cls.other_client.call('config','apply')
        cls.other_client.logout()
        ###################################################################

        ###################################### Configuration of the primary
        # Check that the EW has a license
        cls.checkAndUploadLicense(Test.cluster_ha["secondary"])

        # Connect to the localhost nucentral
        cls.client = cls.createClient()

        # We apply an configuration prior the HA configuration & join to
        # see if it will be replicated
        for call in cls.prior_configuration:
            cls.client.call(*call)

        # Save original configuration
        serialized = cls.client.call('network','getNetconfig')
        cls.orig=deepcopy(serialized)
        netcfg = deserialize(serialized)

        # Let's synchronize our watches
        cls.client.call('ntp',
                        'setNtpConfig',
                        {
                            'ntpservers': u'172.16.0.1',
                            'isFrozen': False
                        },
                        u'message')
        cls.client.call('ntp', 'syncTime')

        # Configure the network according to the input script
        serialized = cls.configure_network(serialized)

        # Configure the HA on the primary
        cls.client.call('ha',
                        'configureHA',
                        cls.primary_ha_configuration,
                        u'message')

        cls.client.call("network","setNetconfig",serialized, "none")
        cls.client.call("config","apply")
        ###################################################################

        ############################################################## Join
        # Fetch and save some of the configurations for comparison purposes
        cls.config=deepcopy(cls.client.call("config","get"))

        # Join

        ###################################################################

    @classmethod
    def teardown_class(cls):
        """
            This method is called once when all tests have been done.
            It restores the saved configuration.
        """
        cls.client.call('network','setNetconfig',cls.orig,'pas de message')
        cls.client.call('config','apply')
        cls.client.logout()

        # Let's check that eth0 isn't affected by our changes
        a = 0
        while a < 200:
            with open("/sys/class/net/eth0/operstate","r") as fd:
                state = fd.readlines()
                assert "up\n" in state, "eth0 changes when it shouldn't"
            sleep(0.2)
            a+=1

        Test.cleanMyDir(cls.test_path)
        Test.teardown_class()
