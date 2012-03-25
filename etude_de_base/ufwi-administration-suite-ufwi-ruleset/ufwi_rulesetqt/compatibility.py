"""
Copyright (C) 2009-2011 EdenWall Technologies

This file is part of NuFirewall. 
 
 NuFirewall is free software: you can redistribute it and/or modify 
 it under the terms of the GNU General Public License as published by 
 the Free Software Foundation, version 3 of the License. 
 
 NuFirewall is distributed in the hope that it will be useful, 
 but WITHOUT ANY WARRANTY; without even the implied warranty of 
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the 
 GNU General Public License for more details. 
 
 You should have received a copy of the GNU General Public License 
 along with NuFirewall.  If not, see <http://www.gnu.org/licenses/>
"""

from logging import warning as log_warning
from ufwi_rpcd.common import tr
from ufwi_rpcd.client import RpcdError
from ufwi_ruleset.version import VERSION as CLIENT_VERSION

SUPPORTED_VERSIONS = (
    "3.0m3", "3.0rc",
    "3.0.1", "3.0.2", "3.0.3", "3.0.4", "3.0.5", "3.0.6")

class Compatibility:
    def __init__(self, window):
        self.window = window
        self.client = window.client
        self.getVersions()
        self.getFeatures()

    def getVersions(self):
        self.client_version = CLIENT_VERSION
        client_attr = {
            'version': self.client_version,
            'mode': 'GUI2',
        }
        try:
            server_attr = self.client.call("ufwi_ruleset", "setupClient", client_attr)
        except RpcdError, err:
            if err.type != 'CoreError':
                raise
            self.server_version = self.client.call("ufwi_ruleset", "getComponentVersion")
            self.mode = 'GUI'
        else:
            self.server_version = server_attr['version']
            self.mode = server_attr['mode']

        log_warning("Connected to server %s in mode %s" % (self.server_version, self.mode))

    def getFeatures(self):
        self.ipsec_network = True
        self.auth_quality = True
        self.default_decisions = True
        self.set_fusion_service = True
        self.nat_support_accept = True
        self.user_group_name = True
        self.has_move_rule = True
        self.platform = True

        if self.server_version == "3.0.5":
            self.platform = False

        elif self.server_version == "3.0.4":
            self.has_move_rule = False
            self.platform = False

        elif self.server_version == "3.0.3":
            self.user_group_name = False
            self.has_move_rule = False
            self.platform = False

        elif self.server_version == "3.0.2":
            self.nat_support_accept = False
            self.user_group_name = False
            self.has_move_rule = False
            self.platform = False

        elif self.server_version == "3.0.1":
            self.ipsec_network = False
            self.set_fusion_service = False
            self.nat_support_accept = False
            self.user_group_name = False
            self.has_move_rule = False
            self.platform = False

        elif self.server_version == "3.0rc":
            self.default_decisions = False
            self.ipsec_network = False
            self.set_fusion_service = False
            self.nat_support_accept = False
            self.user_group_name = False
            self.has_move_rule = False
            self.platform = False

        elif self.server_version == "3.0m3":
            self.auth_quality = False
            self.default_decisions = False
            self.ipsec_network = False
            self.set_fusion_service = False
            self.nat_support_accept = False
            self.user_group_name = False
            self.has_move_rule = False
            self.platform = False

        if self.server_version not in SUPPORTED_VERSIONS:
            warning = \
                tr("Warning: The server (%s) is more recent "
                   "than the client. "
                   "Please upgrade your client.") \
                % self.client.host
        elif self.server_version != CLIENT_VERSION:
            warning = \
                tr("Warning: The server (%s) is older than "
                   "your client: disabling some features. "
                   "Please upgrade your server.") \
                % self.client.host
        else:
            warning = None

        if warning:
            self.window.error(warning, dialog=True)

