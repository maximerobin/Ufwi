# -*- coding: utf-8 -*-
"""
Copyright (C) 2009-2011 EdenWall Technologies
Written by François TOUSSENEL <ftoussenel AT edenwall.com>

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

$Id: $
"""

from __future__ import with_statement

from ufwi_rpcd.backend.exceptions import ConfigError
from ufwi_rpcd.common.service_status_values import ServiceStatusValues
from ufwi_conf.backend.ufwi_conf_component import AbstractNuConfComponent
from ufwi_conf.common.httpout_cfg import HttpOutConf

class HttpOutComponent(AbstractNuConfComponent):
    NAME = "httpout"
    VERSION = "1.0"
    MASTER_KEY = NAME

    REQUIRES = ('config',)

    CONFIG = { 'host': '',
               'port': '',
               'user': '',
               'password': '',
             }

    CONFIG_DEPENDS = ()

    ROLES = {
        'conf_read': set(('getHttpOutConfig',)),
        'conf_write': set(('setHttpOutConfig',)),
    }

    def read_config(self, *args, **kwargs):
        try:
            serialized = self.core.config_manager.get(self.MASTER_KEY)
        except (ConfigError, KeyError):
            self.warning('HttpOut not configured, default values loaded.')
            self.httpout_cfg = HttpOutConf()
        else:
            self.httpout_cfg = HttpOutConf.deserialize(serialized)

    def apply_config(self, *unused):
        self.read_config()

    def save_config(self, message, context=None):
        with self.core.config_manager.begin(self, context) as cm:
            try:
                cm.delete(self.MASTER_KEY)
            except ConfigError:
                pass
            cm.set(self.MASTER_KEY, self.httpout_cfg.serialize())
            cm.commit(message)

    # Services:

    def service_getHttpOutConfig(self, context):
        return self.httpout_cfg.serialize()

    def service_setHttpOutConfig(self, context, serialized, message):
        self.httpout_cfg = HttpOutConf.deserialize(serialized)
        self.save_config(message, context)

    def service_status(self, context):
        """See service status"""
        return self.NAME, ServiceStatusValues.NOT_A_SERVICE

