# -*- coding: utf-8 -*-
"""
Copyright (C) 2010-2011 EdenWall Technologies
Written by François Toussenel <ftoussenel AT edenwall.com>

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

import os
from twisted.internet.defer import inlineCallbacks
from twisted.internet.threads import deferToThread

from ufwi_rpcd.backend.exceptions import ConfigError
from ufwi_rpcd.backend import tr
from ufwi_rpcd.common import EDENWALL
from ufwi_conf.backend.unix_service import ConfigServiceComponent
from ufwi_conf.backend.unix_service import RunCommandError
from ufwi_conf.common.syslog_export_cfg import SyslogExportConf
from .error import (
    NuConfError,
    SYSLOG_EXPORT_BAD_CONFIGURATION,
)

DEFAULT_SHAREDIR = '/usr/share/ufwi_rpcd'
_ULOGD_CONF = "/etc/ulogd.conf"
_RSYSLOG_CONF = "/etc/rsyslog.d/syslog_export.conf"

class SyslogExportComponent(ConfigServiceComponent):
    """
    Export logs (firewall logs for now) through syslog.
    """
    NAME = "syslog_export"
    MASTER_KEY = NAME
    VERSION = "1.0"

    ACLS = {}

    CONFIG_DEPENDS = ()

    REQUIRES = ('config', )
    if EDENWALL:
        REQUIRES += ('license',)

    ROLES = {
        'conf_read': set(('getSyslogExportConfig', 'runtimeFiles')),
        'conf_write': set(('setSyslogExportConfig',)),
    }

    INIT_SCRIPT = "ulogd"

    TYPES = {}

    def init(self, core):
        ConfigServiceComponent.init(self, core)
        self.core = core
        try:
            self.sharedir = self.core.config.get('CORE', 'sharedir')
        except:
            self.sharedir = DEFAULT_SHAREDIR
        self.script_dir = os.path.join(self.sharedir, 'scripts')
        self.addConfFile(_ULOGD_CONF, 'root:root', '0644')
        self.addConfFile(_RSYSLOG_CONF, 'root:root', '0644')

    def read_config(self, *args, **kwargs):
        try:
            serialized = self.core.config_manager.get(self.MASTER_KEY)
        except (ConfigError, KeyError):
            self.warning(tr('Syslog export not configured, default values loaded.'))
            self.syslog_export_cfg = SyslogExportConf()
        else:
            self.syslog_export_cfg = SyslogExportConf.deserialize(serialized)

    def genConfigFiles(self, responsible):
        servers = self.syslog_export_cfg.servers
        for server in servers:
            server["proto_code"] = "@"
            try:
                if server["protocol"] == "tcp":
                    server["proto_code"] = "@@"
                elif server["protocol"] == "relp":
                    server["proto_code"] = ":omrelp:"
            except KeyError:
                pass
            if "port" not in server:
                server["port"] = 514

        template_variables = {
            'enabled': self.syslog_export_cfg.enabled,
            'components': self.syslog_export_cfg.components,
            'servers': servers,
        }

        self.generate_configfile(template_variables)

    def should_run(self, responsible):
        return True

    @inlineCallbacks
    def apply_config(self, responsible, arg, modified_paths):
        self.read_config()
        yield self.genConfigFiles(responsible)

        for initscript, daemon in ((self.get_initscript(), self.INIT_SCRIPT),
            ("/etc/init.d/rsyslog", 'rsyslog'),):
            cmd = (initscript, 'restart',)
            try:
                yield deferToThread(self.runCommandAsRootAndCheck, cmd)

            except RunCommandError:
                #Why do we ignore errors?
                self.error("Restart of %s server failed." % daemon)

    def save_config(self, message, context=None):
        with self.core.config_manager.begin(self, context) as cm:
            try:
                cm.delete(self.MASTER_KEY)
            except ConfigError:
                pass
            cm.set(self.MASTER_KEY, self.syslog_export_cfg.serialize())
            cm.commit(message)

    def get_ports(self):
        return []

    # Services:
    def service_getSyslogExportConfig(self, context):
        return self.syslog_export_cfg.serialize()

    def service_setSyslogExportConfig(self, context, serialized, message):
        self.syslog_export_cfg = SyslogExportConf.deserialize(serialized)
        valid, error_message = self.syslog_export_cfg.isValidWithMsg()
        if not valid:
            raise NuConfError(SYSLOG_EXPORT_BAD_CONFIGURATION,
                              tr("Error in syslog export configuration.") +
                              " " + error_message)
        self.save_config(message, context)

    def service_runtimeFiles(self, context):
        return {}

    def service_runtimeFilesModified(self, context):
        pass

