#coding: utf-8
"""
Testing config in the case of no HA (implementing templateConfig)

Copyright (C) 2009-2011 EdenWall Technologies
Written by Julien Miotte <jmiotte AT edenwall.com>
$Id:$
"""
from templateConfig import templateConfig, NTP

class TestConfigNoHA(templateConfig):
    @classmethod
    def setup_class(cls):
        """
            This method is called once when the class is first instanciated. It
            sets up the testing conditions, while saving the current configuration.
        """
        templateConfig.setup_class(with_ha=False)

        cls.orig = cls.client.call('nurestore', 'export')[0]

    def test_restore(self):
        """
            Save, apply, than restore and apply.
        """
        assert self.check_nucentral(timeout=60), "Nucentral is not available."
        ip0 = u'172.16.0.10'
        self.set_ntp_conf(ip0)
        self.apply_nuconf()

        self.to_save_ip = u'172.16.0.25'
        self._test_save()
        self._test_restore()
        self._test_apply()

#    def test_restart_restore(self):
#        ip0 = u'172.16.0.10'
#        self.set_ntp_conf(ip0)
#        self.apply_nuconf()
#
#        self.to_save_ip = u'172.16.0.25'
#        self._test_save()
#        self._test_restore()
#        self._test_restart()
#        self._test_apply()

    @classmethod
    def teardown_class(cls):
        """
            This method is called once when all tests have been done.
            It restores the saved configuration.
        """
        assert cls.check_nucentral(timeout=50), "Nucentral is not available."
        cls.client.call('nurestore', 'restore', cls.orig)
        cls.apply_nuconf(force=True)
        templateConfig.teardown_class()
