#coding: utf-8
"""
Copyright (C) 2008-2011 EdenWall Technologies
Written by Michael Scherer <m.scherer AT inl.fr>
           Pierre-Louis Bonicoli <bonicoli AT inl.fr>

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
from __future__ import with_statement

from time import time
from datetime import datetime
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.threads import deferToThread

from ufwi_rpcd.backend.exceptions import ConfigError
from ufwi_rpcd.common.error import exceptionAsUnicode
from ufwi_rpcd.common.error import reraise
from ufwi_rpcd.common import tr, EDENWALL
# from ufwi_rpcd.core.audit import AuditEvent
from ufwi_rpcd.core.context import Context
from ufwi_conf.backend.unix_service import ConfigServiceComponent
from ufwi_conf.backend.unix_service import RunCommandError
if EDENWALL:
    from ufwi_conf.common.ha_statuses import PENDING_PRIMARY, PRIMARY, \
        SECONDARY, PENDING_SECONDARY

from .error import NtpError, NTP_SYNC_ERROR
from .error import NTP_INVALID_CONF, NTP_ERROR_SETTING_DATE

def _ntppeers(responsible, ha_status):
    if not EDENWALL:
        return ()
    if ha_status in (SECONDARY, PENDING_SECONDARY):
        responsible.feedback(tr("Using the primary appliance as a NTP peer."))
        #we are secondary, use the primary
        return ('5.0.0.1', )
    if ha_status in (PRIMARY, PENDING_PRIMARY):
        #we are primary, use the 2ndary
        responsible.feedback(tr("Using the secondary appliance as a NTP peer."))
        return ('5.0.0.2', )
    responsible.feedback(tr("No ntp peer."))
    return ()

class NtpComponent(ConfigServiceComponent):
    """
    Component to manage the NTP server, and synchronize the time
    """
    NAME = "ntp"
    VERSION = "1.0"

    REQUIRES = ('config', )

    PIDFILE = "/var/run/ntpd.pid"
    EXE_NAME = "ntpd"
    INIT_SCRIPT = "ntp"

    CONFIG = {
        'ntpservers': '0.pool.ntp.org 1.pool.ntp.org 2.pool.ntp.org',
        'isFrozen': False,
    }

    CONFIG_DEPENDS = ()

    ROLES = {
        'conf_read': set(('getNtpConfig', 'status', 'getServerTime',)),
        'conf_write': set(('@conf_read', 'setNtpConfig', 'syncTime')),
        'multisite_read': set(("@conf_read",)),
        'multisite_write': set(("@multisite_read",)),
        'log_read': set(('getServerTime',)),
    }

    ACLS = {
        'ha': frozenset(('syncTime', 'getHAMode',)),
    }

    def __init__(self):
        ConfigServiceComponent.__init__(self)
        self.addConfFile('/etc/ntp.conf', 'root:root', '0644')

    # called by ConfigServiceComponent.init(...)
    def read_config(self, *args, **kwargs):
        try:
            self.CONFIG = self.core.config_manager.get(self.NAME)
            if 'isFrozen' not in self.CONFIG:
                self.CONFIG['isFrozen'] = False
        except ConfigError:
            self.debug("config not loaded, will generate default configuration")
            #default config
            self.CONFIG = dict(NtpComponent.CONFIG)

    def verify_config(self):
        pass

    def get_ports(self):
        return [ {'proto':'udp', 'port': 123}, ]

    # Services
    def service_getNtpConfig(self, context):
        return self.CONFIG

    def service_setNtpConfig(self, context, config, message):
        """
        Raise NtpError if parameters are invalid

        servers: list of servers separated by space
        """
        # TODO use abstractConf
        if 'ntpservers' not in config:
            raise NtpError(NTP_INVALID_CONF, "missing key 'ntpservers'")
        if (not isinstance(config['ntpservers'], basestring)
           or not config['ntpservers']):
            raise NtpError(NTP_INVALID_CONF, "one ntp server is required")
        if 'isFrozen' not in config:
            raise NtpError(NTP_INVALID_CONF, "missing key 'isFrozen'")

        servers = config['ntpservers'].lower()
        for serv in servers.split(' '):
            if not self.check_ip_or_domain(serv):
                raise NtpError(NTP_INVALID_CONF,
                    tr("invalid ntpserver: %s - does not match a valid IP or domain") % serv)

        self.CONFIG['ntpservers'] = servers
        self.CONFIG['isFrozen'] = bool(config['isFrozen'])
        self.save_config(message)

    def service_setDate(self, context, date):
        #check begin
        if not date:
            raise NtpError(NTP_ERROR_SETTING_DATE, "No date supplied?")
        split_date = date.split('.', 1)
        if len(split_date) > 0:
            datetime_feed, float_part = split_date
            try:
                float('0.%s' % float_part)
            except ValueError:
                raise NtpError(
                    NTP_ERROR_SETTING_DATE,
                    "Invalid date format received. Got '%s'." % date
                    )
        else:
            datetime_feed = split_date[0]
        try:
            datetime.strptime(datetime_feed, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise NtpError(
                NTP_ERROR_SETTING_DATE,
                "Invalid date format received. Got '%s', expected "
                "'%%Y-%%m-%%d %%H:%%M:%%S.floating_part'." % date
                )
        #check end

        args = '--set=%s' % date
        try:
            self.runCommandAsRootAndCheck(['date', args])
        except RunCommandError, err:
            reraise(NtpError(NTP_ERROR_SETTING_DATE, unicode(err)))

    @inlineCallbacks
    def service_syncTime(self, context, server=None):
        """
        Synchronize immediately with the upstream server
        """
        # TODO lock
        #        if self.lock.can_acquire
        # default servers in /etc/ntp.conf will be used if not previously configured
        newtime = yield deferToThread(self.doSyncTime, server)

        # try/finally to sync secondary cluster item asap,
        # and generate the event later whatever happens.
        try:
            yield self.ha_time_sync()
        finally:
            pass
            # event = AuditEvent.fromNTPSync(context)
            # self.core.audit.emit(event)

        returnValue(newtime)

    def service_getServerTime(self, context):
        return self.getTimestamp()
    # Services

    def apply_config(self, responsible, paths, arg=None):
        """
        update and apply configuration

        Callback for config manager
        """
        self.warning("Reconfiguring NTP server (called with paths %s)" % paths)
        return self.updateRunningConf(responsible)

    @inlineCallbacks
    def updateRunningConf(self, responsible):
        """
        generate conf files and restart service
        """
        stop_command, start_command = map(
            self.gen_actionCommand, ("stop", "start")
            )

        #runCommandAsRootAndCheck raises in case of an error (perfect!)
        yield deferToThread(self.runCommandAsRootAndCheck, stop_command)

        ntpservers = self.CONFIG['ntpservers'].split(' ')
        responsible.feedback(
            tr("Reference servers: %(NTPSERVERS)s"),
            NTPSERVERS=', '.join(ntpservers)
            )

        ha_status = None
        context = Context.fromComponent(self)
        if EDENWALL and self.core.hasComponent(context, 'ha'):
            try:
                ha_status = yield self.core.callService(context, 'ha', 'getHAMode')
            except Exception, err:
                self.error(exceptionAsUnicode(err))
        peers = _ntppeers(responsible, ha_status)

        template_variables = {
            'ntpservers' : self.CONFIG['ntpservers'].split(' '),
            'peers': peers,
            }
        self.generate_configfile(template_variables)

        yield deferToThread(self.runCommandAsRootAndCheck, start_command)

    def doSyncTime(self, server=None):
        try:
            self.runCommandAsRootAndCheck([self.get_initscript(), 'stop'])
            if server is None:
                self.runCommandAsRootAndCheck(['/usr/sbin/ntpdate-debian'])
            else:
                self.runCommandAsRootAndCheck(['/usr/sbin/ntpdate', '-b', server])
        except RunCommandError, err:
            raise NtpError(NTP_SYNC_ERROR, err.output)
        finally:
            self.runCommandAsRootAndCheck([self.get_initscript(), 'start'])

        return self.getTimestamp()

    def getTimestamp(self):
        date = time()
        return unicode(date)

    def logError(self, fail):
        self.writeError(fail)
        return fail
