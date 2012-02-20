# -*- coding: utf-8 -*-
"""
Copyright (C) 2009-2011 EdenWall Technologies
Written by Romain Bignon <romain AT inl.fr>

$Id$
"""

from .common.firewall import MultiSiteFirewall
import time

class Firewall(MultiSiteFirewall):

    TIMEOUT = 10*60

    # Constants
    ATTR = ['hostname', 'state', 'cert', 'client_cert', 'cacert', 'error', 'last_seen', 'categories']

    def __init__(self, component, core, module_name, name, attr):
        # attributes
        self.state = MultiSiteFirewall.OFFLINE
        self.cert = ''
        self.client_cert = ''
        self.cacert = ''
        self.last_seen = 0
        self.error = ""
        self.categories = {}
        MultiSiteFirewall.__init__(self, component, core, module_name, name, attr)

    def has_been_seen(self):
        self.last_seen = int(time.time())

    def getState(self):
        if self.last_seen != 0 and \
                         not self.state in (MultiSiteFirewall.OFFLINE, MultiSiteFirewall.ERROR) and \
                         self.last_seen + self.TIMEOUT <= time.time():
            self.state = MultiSiteFirewall.ERROR
            if self.state == self.REGISTERING:
                self.error = "Server isn't available."
            else:
                self.error = "Connection timeout."
            self.save()

        return self.state

    def settings(self, vpn_network, vpn_port, multisite_host, multisite_port):
        return {
            'cert': self.cert,
            'client_cert': self.client_cert,
            'cacert': self.cacert,
            'vpn_network': str(vpn_network),
            'vpn_port': vpn_port,
            'multisite_host': multisite_host,
            'multisite_port': multisite_port,
        }
