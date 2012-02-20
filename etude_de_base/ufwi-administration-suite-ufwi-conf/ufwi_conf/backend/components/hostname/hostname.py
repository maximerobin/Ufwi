# -*- coding: utf-8 -*-
"""
Copyright (C) 2008-2011 EdenWall Technologies
Written by Michael Scherer <m.scherer AT inl.fr>
           Feth Arezki <f.arezki AT edenwall.com>

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

import re
import socket
from copy import deepcopy
from socket import gethostname
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.threads import deferToThread

from ufwi_rpcd.core.context import Context
from ufwi_rpcd.backend.exceptions import ConfigError
from ufwi_rpcd.common import EDENWALL, tr
from ufwi_rpcd.common.service_status_values import ServiceStatusValues
from ufwi_conf.backend.unix_service import ConfigServiceComponent
from ufwi_conf.backend.unix_service import RunCommandError
from ufwi_conf.common.hostnamecfg import CHANGEABLE, CHANGE_DISCOURAGED, \
    NOT_CHANGEABLE
from ufwi_conf.common.user_dir import NuauthCfg

if EDENWALL:
    from ufwi_conf.backend.ha import readHaType
    from ufwi_conf.common.ha_base import getHostnameFormatHA
    from ufwi_conf.common.ha_statuses import ENOHA, PENDING_PRIMARY, PRIMARY

from .errors import BadNameError, NameFrozenError

SEP = u'.'
class HostnameComponent(ConfigServiceComponent):
    NAME = "hostname"
    VERSION = "1.0"

    INIT_SCRIPT = "/bin/true"
    CONFIG = { 'hostname' : '', 'changeable': CHANGEABLE}
    CONFIG_DEPENDS = ()

    REQUIRES = ('config',)
    ROLES = {
        'conf_read': set(('getHostnameConfig', 'getShortHostname',
            'getPrimaryHostname')),
        'conf_write': set(('setShortHostname',)),
    }

    ACLS = {
        'nuauth': frozenset(('getNuauthConfig',))
        }

    def __init__(self):
        ConfigServiceComponent.__init__(self)
        self.empty_conf = False
        self.name_fmt = getHostnameFormatHA(ENOHA) # default fmt

    def init(self, core):
        ConfigServiceComponent.init(self, core)
        self.addConfFile('/etc/hostname', 'root:root', '0644')

    def read_config(self, *args, **kwargs):
        try:
            self.CONFIG = self.core.config_manager.get(self.NAME)
        except ConfigError:
            self._discover_hostname()
            self.empty_conf = True

        if EDENWALL:
            ha_type = self._readHaType()
            self.name_fmt = getHostnameFormatHA(ha_type)

    def _readHaType(self):
        return readHaType(self.core.config.get('CORE', 'vardir'))

    @inlineCallbacks
    def apply_config(self, responsible, arg, modified_paths):
        """
        Callback for config manager
        """
        self.read_config()
        cfg = self.getHostnameConfig()
        self.generate_configfile(cfg)

        new_hostname = cfg['hostname']

        if gethostname() == new_hostname:
            responsible.feedback(tr("Server name unchanged"))
            returnValue(None)

        responsible.feedback(tr("Changing server name to %(new_name)s"), new_name=new_hostname)

        yield deferToThread(
            self.runCommandAsRootAndCheck,
            ['/bin/hostname', cfg['hostname']]
        )

        responsible.feedback(tr("Restarting internal logging daemon"))
        cmd = ('/etc/init.d/rsyslog', 'restart')
        try:
            yield deferToThread(self.runCommandAsRootAndCheck, cmd)
        except RunCommandError:
            self.error("Restart of rsyslog server failed.")
            raise

    def checkServiceCall(self, context, service_name):
        if 'saveConfiguration' == service_name \
        and context.isComponentContext() \
        and 'ha' == context.component.name:
            # config component doesn't need a lock here
            return
        ConfigServiceComponent.checkServiceCall(self, context, service_name)

    def _discover_hostname(self):
        hostname = socket.gethostname()
        #TODO: prevent user from entering a hostname ending with -secondary
        hostname = re.sub(r"-secondary$", "", hostname)
        self.CONFIG = {
            'hostname': hostname,
            'changeable': CHANGEABLE,
            }

    def getHostnameConfig(self):
        """
        return hostname and 'frozen' info
        take in account ha status
        """
        cfg = deepcopy(self.CONFIG)
        cfg['hostname'] = self.getShortHostname()
        return cfg

    def getShortHostname(self):
        """
        return hostname
        """
        return self.name_fmt % self.CONFIG['hostname']

    ## Services
    def service_getPrimaryHostname(self, context):
        """
        return primary hostname
        """
        return self.CONFIG['hostname']

    # Services
    @inlineCallbacks
    def service_setShortHostname(self, context, hostname, message):
        """
        @arg hostname (not fqdn)
        set hostname of the server
        """
        if self._isChangeForbidden():
            if self.doesChange(hostname):
                raise NameFrozenError()
            #If there is no change AND name change is forbidden, then we
            #let go silently.
            #This quickly works around a bug in the interface:
            #the interface is saving hostname whenever dns servers are being saved too.
            returnValue(None)

        #even in there is no change, we'll set this as changed value.
        yield self.setShortHostname(hostname, message)

    @inlineCallbacks
    def changeable(self):
        if self._isChangeForbidden():
            returnValue(NOT_CHANGEABLE)
        context = Context.fromComponent(self)
        serialized_nuauthcfg = yield self.core.callService(
            context,
            "nuauth",
            "getNuauthConfig"
            )
        nuauthcfg = NuauthCfg.deserialize(serialized_nuauthcfg)
        changeable = CHANGE_DISCOURAGED if nuauthcfg.hasAD() else CHANGEABLE
        returnValue(changeable)

    @inlineCallbacks
    def service_getHostnameConfig(self, context):
        """
        return hostname and 'frozen' info
        """
        # XXX FIXME a better algo should be used
        if self.empty_conf:
            self.empty_conf = False
            self.save_config('write hostname configuration')
        info = self.getHostnameConfig()

        info['changeable'] = yield self.changeable()

        returnValue(info)

    def service_getShortHostname(self, context):
        """
        Return the first part of the hostname of the server
        """
        # XXX FIXME a better algo should be used
        if self.empty_conf:
            self.empty_conf = False
            self.save_config('write hostname configuration')
        return self.getShortHostname()

    def service_discoverHostname(self, context):
        """ Discover the domain name of the computer """
        self._discover_hostname()
        return ''

    def service_status(self, context):
        """See service status"""
        return self.NAME, ServiceStatusValues.NOT_A_SERVICE
    ##

    @inlineCallbacks
    def setShortHostname(self, hostname, message):
        hostname = hostname.strip()
        if not self.check_hostname(hostname):
            raise BadNameError("%s is not a valid hostname" % unicode(hostname))

        if SEP in hostname:
            hostname, useless = hostname.split(SEP, 1)
        self.CONFIG['hostname'] = hostname
        yield deferToThread(self.save_config, message)

    def _isChangeForbidden(self):
        return EDENWALL and self._readHaType() in (PENDING_PRIMARY, PRIMARY)

    def doesChange(self, new_hostname):
        """
        Does this hostname constitute a change to current hostname?
        """
        return self.CONFIG.get('hostname') != new_hostname

