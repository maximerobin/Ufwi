# -*- coding: utf-8 -*-
"""
Copyright (C) 2008-2011 EdenWall Technologies
Written by Michael Scherer <m.scherer AT inl.fr>
Written by Feth AREZKI <farezki AT inl.fr>

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

$Id$
"""

from __future__ import with_statement

from twisted.internet.threads import deferToThread

from ufwi_rpcd.core.config.responsible import CONFIG_MODIFICATION, \
    CONFIG_AUTOCONFIGURATION
from ufwi_rpcd.backend.exceptions import ConfigError
from ufwi_rpcd.common.service_status_values import ServiceStatusValues
from ufwi_conf.backend.dnsutils import dig
from ufwi_conf.backend.resolvcfg_autoconf import ResolvCfgAutoconf
from ufwi_conf.backend.unix_service import ConfigServiceComponent
from ufwi_conf.common.resolvcfg import deserialize, ResolvError

class ResolvComponent(ConfigServiceComponent):
    NAME = "resolv"
    VERSION = "1.0"

    REQUIRES = ('config',)

    INIT_SCRIPT = "/bin/true"

    CONFIG = { 'nameservers': '',
               'domain': ''
             }
    CONFIG_DEPENDS = ()

    ROLES = {
        'conf_read': set(('getResolvConfig', 'getRunningConfig', 'getDomain', 'test')),
        'conf_write': set(('setResolvConfig',)),
    }

    def __init__(self):
        ConfigServiceComponent.__init__(self)
        self.addConfFile('/etc/resolv.conf', 'root:root', '0644')
        self.key_exists = False
        self.resolvcfg = ResolvCfgAutoconf()

    def init(self, core):
        ConfigServiceComponent.init(self, core)
        if not self.key_exists:
            self.useDefaultConf()

    def read_config(self, *args, **kwargs):
        try:
            config = self.core.config_manager.get(self.NAME)
            self.key_exists = True
        except ConfigError:
            self.key_exists = False
            self.resolvcfg = ResolvCfgAutoconf()
        else:
            self.resolvcfg = deserialize(config)

    def apply_config(self, responsible, paths, arg=None):
        """
        Callback for config manager
        """
        nameservers = []
        for dns in [self.resolvcfg.nameserver1, self.resolvcfg.nameserver2]:
            if dns:
                nameservers.append(dns)

        template_variables = {
            'domain' : self.resolvcfg.domain,
            'nameservers' : ('127.0.0.1',)
        }
        self.generate_configfile(template_variables)

    def rollback_config(self, responsible, paths, arg=None):
        """
        same as apply but commit and save default conf if current conf is empty
        """
        # FIXME must be done but not supported yet
        #if not self.key_exists:
        #    self.useDefaultConf()
        return self.apply_config(responsible, paths, arg=arg)

    def useDefaultConf(self):
        """
        commit & apply default conf
        """
        self.debug("take in account default configuration")
        self.save_config(
            CONFIG_AUTOCONFIGURATION,
            "Resolv module Autoconfiguration"
            )
        self.core.config_manager.signalAutoconf()

    def save_config(self, action, message, context=None):
        with self.core.config_manager.begin(self, context, action=action) as cm:
            try:
                cm.delete(self.NAME)
            except ConfigError:
                pass
            cm.set(self.NAME, self.resolvcfg.serialize())
            cm.commit(message)

    def getDomain(self):
        return self.resolvcfg.domain

    def service_getDomain(self, context):
        return self.getDomain()

    # Services
    def service_getResolvConfig(self, context):
        return self.resolvcfg.serialize()

    def service_getRunningConfig(self, context):
        return self.core.config_manager.get(
            self.NAME,
            which_configuration='applied'
            )

    def service_setResolvConfig(self, context, serialized, message):
        resolvcfg = deserialize(serialized)
        invalid_data = resolvcfg.isInvalid()
        if not invalid_data:
            self.resolvcfg = resolvcfg
            self.save_config(CONFIG_MODIFICATION, message, context)
        else:
            raise ResolvError("Error : '%s'" % invalid_data)

    def service_status(self, context):
        """See service status"""
        return self.NAME, ServiceStatusValues.NOT_A_SERVICE

    def service_test(self, context, data):
        server = data.get('server')
        query = data.get('query')
        #TODO: validate both variables as IP or FQDN
        return deferToThread(dig, self, **{
            'defaultserver': self.resolvcfg.nameserver1,
            'server': server,
            'query': query}
            )

