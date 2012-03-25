#coding: utf-8
"""
Testing config in the case of HA (implementing templateConfig)

Copyright (C) 2009-2011 EdenWall Technologies
Written by Julien Miotte <jmiotte AT edenwall.com>
$Id:$
"""
from templateConfig import templateConfig, NTP

class TestConfigHA(templateConfig):
    """
        In this test we are going to save, apply, reset configurations and check
        the integrity of the configuration at any given time.
    """
    @classmethod
    def setup_class(cls):
        """
            This method is called once when the class is first instanciated. It
            sets up the testing conditions, while saving the current
            configuration.
        """
        templateConfig.setup_class(with_ha=True)
