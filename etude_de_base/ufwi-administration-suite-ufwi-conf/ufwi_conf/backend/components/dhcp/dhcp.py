# -*- coding: utf-8 -*-
"""
Copyright (C) 2008-2011 EdenWall Technologies
Written by Michael Scherer <m.scherer AT inl.fr>

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

from os.path import exists
from twisted.internet.defer import inlineCallbacks
from twisted.internet.threads import deferToThread
from twisted.python.failure import Failure

from ufwi_rpcd.backend.exceptions import ConfigError
from ufwi_rpcd.common.error import exceptionAsUnicode
from ufwi_rpcd.common import tr
from ufwi_rpcd.core.context import Context
from ufwi_conf.backend.unix_service import ConfigServiceComponent
from ufwi_conf.common.dhcpcfg import deserialize
from ufwi_conf.common.dhcpcfg import DHCPCfg
from ufwi_conf.common.dhcpcfg import DHCPError as CommonDHCPError
from ufwi_conf.common.ha_base import PRIMARY_ADDR, SECONDARY_ADDR
from ufwi_conf.common.ha_statuses import ENOHA, PRIMARY, SECONDARY
from ufwi_conf.common.netcfg_rw import deserialize as deserializeNetCfg

from .error import DHCPError

CUSTOM_DHCP = '/etc/dhcp3/dhcpd-custom.conf'

class DhcpError(Exception):
    pass

class DhcpComponent(ConfigServiceComponent):
    """
    Dhcp: manage the dhcp server component
    """

    #apply_config is inherited

    NAME = "dhcp"
    VERSION = "1.0"

    REQUIRES = ('config', 'network', 'resolv')

    PIDFILE = "/var/run/dhcpd.pid"
    EXE_NAME = "dhcpd3"

    INIT_SCRIPT = "dhcp3-server"
    CONFIG = { 'start_ip' : '',
               'end_ip' : '',
             }

    CONFIG_DEPENDS = frozenset(('network', 'ha',))

    ACLS = {
        'network': set(('getNetconfig',)),
        'dhcp': set(('start', 'stop',)),
        'ha': set(('getHAMode',)),
    }

    ROLES = {
        'conf_read': set(("getDhcpConfig",)),
        'conf_write': set(("setDhcpConfig",)),
        'multisite_read': set(("status",)),
    }

    check_start_ip = ConfigServiceComponent.check_ip
    check_end_ip = ConfigServiceComponent.check_ip

    def __init__(self):
        self.dhcpcfg = None
        ConfigServiceComponent.__init__(self)

    def init(self, core):
        ConfigServiceComponent.init(self, core)
        self.addConfFile('/etc/dhcp3/dhcpd.conf', 'root:root', '0644')
        self.addConfFile('/etc/ha.d/resource.d/omshell_dhcpd', 'root:root', '0755')

    def should_run(self, responsible):
        if not self.dhcpcfg.enabled:
            responsible.feedback(tr(
                "Will not start the DHCP server: not enabled by user."
            ))
            return False

        if not len(self.dhcpcfg.ranges) > 0 and not self.__hascustom():
            responsible.feedback(tr(
                "Will not start the DHCP server: enabled but no DHCP range configured."
            ))
            return False

        responsible.feedback(tr(
            "Will start the DHCP server."
        ))
        return True

    @inlineCallbacks
    def read_config(self, responsible, *args, **kwargs):
        if (responsible is not None) \
        and (responsible.caller_component == "dhcp"):
            return

        try:
            serialized_dhcpcfg = self.core.config_manager.get(self.NAME)
        except ConfigError:
            dhcpcfg = DHCPCfg()
            self.debug("Could not read a DHCP config. Defaults loaded.")
        else:
            context = Context.fromComponent(self)
            serialized_netcfg = yield self.core.callService(context, 'network', 'getNetconfig')
            dhcpcfg = self._deserializeDhcpConfig(serialized_netcfg, serialized_dhcpcfg)
        self._setDhcpConfig(dhcpcfg)

    def service_getDhcpConfig(self, context):
        return self.dhcpcfg.serialize()

    def raiseErrors(self, data):
        if isinstance(data, Failure):
            data.raiseException()

    def service_setDhcpConfig(self, context, dhcpConfig, message):
        defer = self.core.callService(context, 'network', 'getNetconfig')
        defer.addCallback(self._deserializeDhcpConfig, dhcpConfig)
        defer.addCallback(self._saveDhcpConfig, message, context)
        defer.addBoth(self.raiseErrors)
        return defer

    def _deserializeDhcpConfig(self, serializedNetCfg, serializedDhcpConfig):
        try:
            dhcpconfig = deserialize(serializedDhcpConfig, deserializeNetCfg(serializedNetCfg))
        except CommonDHCPError:
            raise DHCPError(*CommonDHCPError.args)
        ok, msg = dhcpconfig.isValidWithMsg()
        if not ok:
            raise DHCPError(msg)
        return dhcpconfig

    def _setDhcpConfig(self, config):
        self.dhcpcfg = config

    def _saveDhcpConfig(self, dhcpcfg, message, context):
        if not dhcpcfg.isValid():
            raise DHCPError('Invalid DhcpConfig')
        self._setDhcpConfig(dhcpcfg)

        with self.core.config_manager.begin(self, context) as cm:
            try:
                cm.delete(self.NAME)
            except ConfigError:
                #Means the value does not exist in the first place
                pass
            cm.set(self.NAME, dhcpcfg.serialize())
            cm.commit(message)

    def get_ports(self):
        return [{'proto':'udp',
                 'port': 67},
                {'proto':'udp',
                 'port': 68}, ]

    def __hascustom(self):
        return exists(CUSTOM_DHCP)

    @inlineCallbacks
    def genConfigFiles(self, responsible):
        if self.__hascustom():
            custom = CUSTOM_DHCP
        else:
            custom = False

        try:
            context = Context.fromComponent(self)
            ha_status = yield self.core.callService(context, 'ha', 'getHAMode')
        except Exception, err:
            self.error(exceptionAsUnicode(err))
            ha_status = ENOHA

        ranges_nb = len(self.dhcpcfg.ranges)
        if ranges_nb:
            responsible.feedback(
                tr("Configuring with %(NUMBER)s ranges."),
                NUMBER=ranges_nb
            )
        if ranges_nb and ha_status in (PRIMARY, SECONDARY):
            responsible.feedback(
                tr("Failover mode activated.")
            )

        if custom:
            responsible.feedback(
                tr("Including customized file in configuration.")
            )

        template_variables = {
            'ranges' : self.dhcpcfg.ranges,
            'default_lease_time' : '36000',
            'max_lease_time' : '72000',
            'log_facility' : 'local7',
            'custom': custom,
            'ha_status': ha_status,
            'PRIMARY_ADDR': PRIMARY_ADDR,
            'SECONDARY_ADDR': SECONDARY_ADDR,
        }

        self.generate_configfile(template_variables)

    @inlineCallbacks
    def service_restart(self, context):
        """
        override UnixServiceComponent.service_restart
        """
        try:
            yield deferToThread(self.runCommandAsRootAndCheck, [self.get_initscript(), 'restart'])
        except Exception:
            if len(self.dhcpcfg.ranges) > 0:
                raise
            #Ignore errors if the dhcp server is not
            #configured by us but by the custom file

    def service_runtimeFiles(self, context):
        del context
        return  {
            'deleted': (CUSTOM_DHCP,),
            'added' : ((CUSTOM_DHCP, 'text'),)
            }

    def service_runtimeFilesModified(self, context):
        del context
        if self.__hascustom():
            self.info("* DHCP custom file restored *")

