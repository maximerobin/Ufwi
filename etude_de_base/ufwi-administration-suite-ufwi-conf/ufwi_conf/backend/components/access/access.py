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
from itertools import chain

from ufwi_rpcd.backend.exceptions import ConfigError
from ufwi_rpcd.common.defer import gatherResults
from ufwi_rpcd.core.context import Context

from ufwi_conf.backend.ufwi_conf_component import AbstractNuConfComponent
from ufwi_conf.common.netcfg import deserializeNetCfg
from ufwi_conf.common.access_cfg import AccessConf, OPEN_BY_DEFAULT, CLOSED_NETWORKS
from ufwi_rpcd.common.abstract_cfg import DatastructureIncompatible

from .error import AccessError

# Error codes
MISSING_ADMIN_ACCESS = 1

LOCALFW_FILENAME = 'access'

"""
Value returned by component.getPorts() must be constant for every component.
However if a compoment needs to change the return value of getPorts() it's name
should be mentionned in REQUIRES and in config.subscribe().
"""

class AccessComponent(AbstractNuConfComponent):
    NAME = "access"
    VERSION = "1.0"

    REQUIRES = ('config', 'localfw' )

    CONFIG = { }

    CONFIG_DEPENDS = frozenset(('network',))

    ROLES = {
        'conf_read': set(('getConfig', 'getServices')),
        'conf_write': set(('setConfig', 'applyRules')),
    }
    ACLS = {
        'status': set(('getStatus',)),
        'network': set(('getNetconfig',)),
        'localfw': set(('open', 'clear', 'addFilterRule', 'apply', 'close')),
        # FIXME: localfw should delegate the permissions
        'ufwi_ruleset': set(('reapplyLastRuleset',)),
        '*': set(('getPorts',)),
    }

    HARDCODED_SERVICES = {
        'ping_access': [
            {'proto':'icmp', 'icmp_type': 8},      # IPv4
            {'proto':'icmpv6', 'icmpv6_type': 128}, # IPv6 (Echo Request)
        ],
        # streaming port (udp) is set in read in ufwi_rpcd configuration
        'ufwi_rpcd_access': [
         {'proto':'tcp', 'port': 8443},
         {'proto':'udp', 'port': None}],
        # streaming port (udp) is set in read in ufwi_rpcd configuration
        'snmpd': [
         {'proto':'tcp', 'port': 161},
         {'proto':'udp', 'port': 161}],
        'SSH': [
            {'proto': 'tcp', 'port': 22}],
    }

    def init(self, core):
        AbstractNuConfComponent.init(self, core)
        self.core = core

        # dict: service name => port list
        self.services = None

        # Read streaming port from the config
        port = core.config.getint('CORE', 'streaming_udp_port')
        self.HARDCODED_SERVICES['ufwi_rpcd_access'][1]['port'] = port

    def applyRules(self, save=False, already_read=False):
        if not already_read:
            self.read_config(None)
        context = Context.fromComponent(self)

        self.debug('First loading of configuration')
        defer = self.update()
#       FIXME: Check permissions?
#        defer.addCallback(lambda unused: self.checkPermissions(self.permissions))
        defer.addCallback(self._applyGetNetcfg, context)
        if save:
            defer.addCallback(self._save_config)
        return defer

    def apply_config(self, responsible, callback_arg, paths):
        return self.applyRules(already_read=True)

    def _applyGetNetcfg(self, unused, context):
        defer = self.core.callService(context, 'network', 'getNetconfig')
        defer.addCallback(self._applyUseNetCfg, context)
        return defer

    def _clearRules(self, unused, context):
        return self.core.callService(context, 'localfw', 'clear')

    def _createRules(self, unused, netcfg, context):
        defer_list = []
        for service, networks in self.access_cfg.permissions.iteritems():
            ports = self.services[service]
            for port in ports:
                for interface, network in networks:
                    protocol = port['proto']
                    ipv6 = (network.version() == 6)
                    rule = {
                        'chain': 'INPUT',
                        'decision': 'ACCEPT',
                        'ipv6': ipv6,
                        'protocol': protocol,
                        'sources': [unicode(network)],
                        'input': interface,
                    }
                    if protocol == 'icmp':
                        if ipv6:
                            # ICMP is for IPv4
                            continue
                        rule['icmp_type'] = port['icmp_type']
                    elif protocol == 'icmpv6':
                        if not ipv6:
                            # ICMPv6 is for IPv6
                            continue
                        rule['icmpv6_type'] = port['icmpv6_type']
                    elif 'port' in port:
                        rule['dport'] = port['port']
                    defer = self.core.callService(context, 'localfw', 'addFilterRule', rule)
                    defer_list.append(defer)
        return gatherResults(defer_list)

    def _applyLocalFW(self, unused, context):
        return self.core.callService(context, 'localfw', 'apply')

    def _closeLocalFW(self, result, context):
        defer = self.core.callService(context, 'localfw', 'close')
        def _finally(unused):
            return result
        defer.addBoth(_finally)
        return defer

    def _applyUseNetCfg(self, netcfg_data, context):
        netcfg = deserializeNetCfg(netcfg_data)

        # FIXME: use LocalFW wrapper
        defer = self.core.callService(context, 'localfw', 'open', LOCALFW_FILENAME)
        defer.addCallback(self._clearRules, context)
        defer.addCallback(self._createRules, netcfg, context)
        defer.addCallback(self._applyLocalFW, context)
        defer.addBoth(self._closeLocalFW, context)
        return defer

    def read_config(self, responsible, *args, **kwargs):
        if (responsible is not None) \
        and (responsible.caller_component == "access"):
            return
        try:
            serialized = self.core.config_manager.get(self.NAME)
            self.access_cfg = AccessConf.deserialize(serialized)
        except (ConfigError, DatastructureIncompatible):
            self.debug("Read config error: create new permissions")
            self.access_cfg = AccessConf()

        # force update
        self.services = None

    def _updateNetworks(self, data):
        netcfg = deserializeNetCfg(data)
        networks = set((interface.system_name, network)
            for interface, network in netcfg.iterKnownNetworks())
        networks |= set(self.access_cfg.custom_networks)
        open_networks = set((interface, network)
            for (interface, network) in networks
            if network not in CLOSED_NETWORKS)
        permissions = self.access_cfg.permissions
        for service in permissions:
            if permissions[service] == True:
                permissions[service] = open_networks
            else:
                # delete old networks
                permissions[service] &= networks

    def _updateServices(self, result, context):
        old_permissions = self.access_cfg.permissions
        network_services, local_services = result
        new_permissions = {}
        self.services = {}
        services = chain(network_services, self.HARDCODED_SERVICES.iterkeys())
        services = list(services)
        for service in services:
            self.services[service] = tuple()
            if service in old_permissions:
                new_permissions[service] = old_permissions[service]
            elif service in OPEN_BY_DEFAULT:
                # opened for all networks by default
                new_permissions[service] = True
            else:
                # new service
                new_permissions[service] = set()
        # delete also the old services
        self.access_cfg.permissions = new_permissions

        defer = self.core.callService(context, 'network', 'getNetconfig')
        defer.addCallback(self._updateNetworks)
        defer.addCallback(self._updatePorts, context)
        return defer

    def _updatePort(self, ports, service):
        self.services[service] = ports

    def _updatePorts(self, unused, context):
        defer_list = []
        for service in self.services:
            try:
                self.services[service] = self.HARDCODED_SERVICES[service]
            except KeyError:
                defer = self.core.callService(context, service, "getPorts")
                defer.addCallback(self._updatePort, service)
                defer_list.append(defer)
        return gatherResults(defer_list)

    def update(self):
        context = Context.fromComponent(self)
        defer = self.core.callService(context, 'status', 'getStatus')
        defer.addCallback(self._updateServices, context)
        return defer

    def _getServices(self, unused=None):
        return self.services

    def service_getServices(self, context):
        defer = self.update()
        defer.addCallback(self._getServices)
        return defer

    def _getConfig(self, unused):
        return self.access_cfg.serialize()

    def service_getConfig(self, context):
        defer = self.update()
        defer.addCallback(self._getConfig)
        return defer

    def save_config(self, message="Save access config", context=None):
        self.info("Saving access config")
        with self.core.config_manager.begin(self, context) as cm:
            try:
                cm.delete(self.NAME)
            except:
                pass
            cm.set(self.NAME, self.access_cfg.serialize())
            cm.commit(message)

    def _save_config(self, unused):
        self.save_config()

    def service_setConfig(self, context, message, config):
        new_conf = AccessConf.deserialize(config)
        valid, errmsg = new_conf.isValidWithMsg()
        if not valid:
           raise AccessError(MISSING_ADMIN_ACCESS, errmsg)
        self.access_cfg = new_conf
        self.save_config(message, context)

    def service_applyRules(self, context):
        return self.applyRules(save=True)

