# -*- coding: utf-8 -*-
"""
Copyright (C) 2008-2011 EdenWall Technologies
Written by Michael Scherer <m.scherer AT inl.fr>
           François Toussenel <ftoussenel AT edenwall.com>

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

from ufwi_rpcd.backend.exceptions import ConfigError
from ufwi_rpcd.backend.process import runCommand
from ufwi_conf.backend.unix_service import ConfigServiceComponent
from ufwi_conf.common.contact_cfg import ContactConf
from ufwi_conf.common.snmpd_cfg import INDEX_V3_AUTHENTICATION_PASS
from ufwi_conf.common.snmpd_cfg import INDEX_V3_AUTHENTICATION_PROTO
from ufwi_conf.common.snmpd_cfg import INDEX_V3_ENCRYPTION_ALGO
from ufwi_conf.common.snmpd_cfg import INDEX_V3_ENCRYPTION_PASS
from ufwi_conf.common.snmpd_cfg import INDEX_V3_USERNAME
from ufwi_conf.common.snmpd_cfg import SnmpdConf

class SnmpdComponent(ConfigServiceComponent):
    NAME = "snmpd"
    MASTER_KEY = NAME
    VERSION = "1.0"

    REQUIRES = ('config', 'contact')

    PIDFILE = "/var/run/snmpd.pid"
    EXE_NAME = "snmpd"
    HARD_STOP_REQUIRED = True

    INIT_SCRIPT = "snmpd"
    CONFIG_DEPENDS = frozenset(('network', 'resolv'))

    ROLES = {
        "conf_read": set(("getSnmpdConfig",)),
        "conf_write": set(("setSnmpdConfig",))
    }

    def __init__(self):
        ConfigServiceComponent.__init__(self)
        self.snmp_users_filename = None

    def get_ports(self):
        return [{'proto':'udp', 'port': 161}]

    def init(self, core):
        ConfigServiceComponent.init(self, core)
        self.core = core
        depend_key = ('contact', 'admin_mail')
        depend_name = 'contact_snmpd'
        for (event, method) in (
            ('modify', self.read_config),
            ('apply', self.apply_config),
            ('rollback', self.apply_config)
            ):
            self.core.config_manager.subscribe(method, depend_name, (),
                                               event, *depend_key)
        self.addConfFile('/etc/default/snmpd', 'root:root', '0644')
        self.addConfFile('/etc/snmp/snmpd.conf', 'root:root', '0644')
        self.snmp_users_filename = "/var/lib/snmp/snmpd.conf"

    def read_config(self, *args, **kwargs):
        try:
            serialized = self.core.config_manager.get(self.NAME)
        except (ConfigError, KeyError):
            self.config = SnmpdConf()
        else:
            self.config = SnmpdConf.deserialize(serialized)
        try:
            serialized = self.core.config_manager.get("contact")
        except (ConfigError, KeyError):
            self.contact_config = ContactConf.defaultConf()
        else:
            self.contact_config = ContactConf.deserialize(serialized)

    def genConfigFiles(self, responsible):
        self.read_config()

        admin_mail = self.contact_config.admin_mail
        if not admin_mail:
            admin_mail = "root@localhost"
        template_variables = {
            'enabled': self.config.enabled,
            'syscontact': admin_mail,
            'syslocation': "EdenWall 4",
            'v2c_list': self.config.v2c_list,
            'v3_list': self.config.v3_list}

        self.generate_configfile(template_variables)

        # Delete all current users and create the ones in the V3 list:
        createUser_lines = ""
        for user in self.config.v3_list:
            createUser_lines += 'createUser %s %s "%s" %s "%s"\n' % (
                user[INDEX_V3_USERNAME],
                user[INDEX_V3_AUTHENTICATION_PROTO],
                user[INDEX_V3_AUTHENTICATION_PASS],
                user[INDEX_V3_ENCRYPTION_ALGO],
                user[INDEX_V3_ENCRYPTION_PASS])
        runCommand(self, ["sed", "-i", "/^usmUser/d",
                          self.snmp_users_filename])
        with open(self.snmp_users_filename, "a") as fd:
            fd.write(createUser_lines)

    def should_run(self, responsible):
        return True

    #apply_config is inherited

    def save_config(self, message, context=None):
        with self.core.config_manager.begin(self, context) as cm:
            try:
                cm.delete(self.MASTER_KEY)
            except ConfigError:
                pass
            cm.set(self.MASTER_KEY, self.config.serialize())
            cm.commit(message)

    # Services:

    def service_getSnmpdConfig(self, context):
        return self.config.serialize()

    def service_setSnmpdConfig(self, context, serialized, message):
        self.config = SnmpdConf.deserialize(serialized)
        self.save_config(message, context)
