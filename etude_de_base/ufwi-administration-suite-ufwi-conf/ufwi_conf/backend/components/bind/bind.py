# -*- coding: utf-8 -*-
"""
Copyright (C) 2008-2011 EdenWall Technologies
Written by Michael Scherer <m.scherer AT inl.fr>
           François Toussenel <ftoussenel AT edenwall.com>
           Pierre-Louis Bonicoli <bonicoli AT edenwall.com>
           Feth Arezki <farezki@edenwall.com>

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

from IPy import IP
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.threads import deferToThread

from ufwi_rpcd.backend.exceptions import ConfigError
from ufwi_rpcd.backend.process import runCommand
from ufwi_rpcd.common import tr
from ufwi_rpcd.core.context import Context
from ufwi_conf.backend.anylist2iplist import iterable2ipset, UnresolvableHost
from ufwi_conf.backend.resolvcfg_autoconf import ResolvCfgAutoconf
from ufwi_conf.backend.unix_service import ConfigServiceComponent
from ufwi_conf.backend.unix_service import RunCommandError
from ufwi_conf.common.resolvcfg import deserialize as resolv_deserialize
from ufwi_conf.common.user_dir import NuauthCfg

from .errors import DNSError

_FEEDBACK_CFG_AD = tr("Configuration: Global zone: %(GLOBAL_SERVERS)s; "
    "AD domain: %(AD_DOMAIN)s; AD controller: %(AD_CONTROLLER)s.")

_FEEDBACK_CFG_SIMPLE = tr("Configuration: Global zone: %(GLOBAL_SERVERS)s.")

_FEEDBACK_DNSERROR_WO_HELPERS = tr("An error occured: None of the DNS servers "
    "in [%(dns_servers_list)s] could provide an IP address record for the name "
    "\"%(name)s\"")

_FEEDBACK_DNSERROR_W_HELPERS = tr("An error occured: None of the DNS servers "
    "in [%(dns_servers_list)s] or [%(dns_additionnal_list)s] could provide an "
    "IP address record for the name \"%(name)s\"")

class BindComponent(ConfigServiceComponent):
    NAME = "bind"
    MASTER_KEY = NAME
    VERSION = "1.0"

    REQUIRES = ('config', 'resolv')

    PIDFILE = "/var/run/bind/run/named.pid"
    EXE_NAME = "named"

    INIT_SCRIPT = "bind9"
    INITRANK_S = 15
    INITRANK_K = 85

    CONFIG_DEPENDS = frozenset(('network', 'resolv'))

    def __init__(self):
        ConfigServiceComponent.__init__(self)
        self.config = {}

    def get_ports(self):
        return [{'proto':'udp',
                 'port': 53},
                {'proto':'tcp',
                 'port': 53}, ]

    def init(self, core):
        ConfigServiceComponent.init(self, core)

        depend_key = ('nuauth_bind', 'nuauth_bind_dependency')
        depend_name = 'nuauth_bind'

        for (event, method) in (
            ('modify', self.read_config),
            ('apply', self.apply_config),
            ('rollback', self.apply_config)
            ):
            self.core.config_manager.subscribe(method, depend_name, (),
                                               event, *depend_key)

        self.addConfFile('/etc/bind/named.conf', 'root:bind', '0644')
        self.addConfFile('/etc/bind/named.conf.local', 'root:bind', '0644')
        self.addConfFile('/etc/bind/named.conf.options', 'root:bind', '0644')

    def read_config(self, *args, **kwargs):

        name = 'nuauth'
        try:
            serialized = self.core.config_manager.get(name)
        except (ConfigError, KeyError):
            self.config[name] = NuauthCfg()
        else:
            self.config[name] = NuauthCfg.deserialize(serialized)

        name = 'resolv'
        try:
            serialized = self.core.config_manager.get(name)
        except (ConfigError, KeyError):
            # XXX should be removed : bind require resolv which already call, save
            # and apply autoconf
            self.config[name] = ResolvCfgAutoconf()
        else:
            self.config[name] = resolv_deserialize(serialized)

    def __previous_nuauth_config(self):
        try:
            return self.core.config_manager.get(
                'nuauth',
                which_configuration='applied'
                )
        except (KeyError, ConfigError):
            return None

    def __nuauth_hadAD(self):
        previous_nuauth = self.__previous_nuauth_config()
        if previous_nuauth is None:
            hadAD = False
            self.debug("There is no previous configuration")
        else:
            try:
                hadAD = NuauthCfg.deserialize(previous_nuauth).hasAD()
                self.debug("Reading previous configuration.")
            except:
                self.debug("Assuming we had an AD previously")
                #Assume True and risk restarting bind for nothing: it is safer
                hadAD = True
        if hadAD:
            self.debug("Conclusion: We had an AD previously.")
        else:
            self.debug("Conclusion: We did not have an AD previously.")
        return hadAD

    def __nuauth_hasAD(self):
        if self.config['nuauth'] is None:
            #assume has AD
            self.debug("No previous config: Assuming AD involved")
            return True
        return self.config['nuauth'].hasAD()

    def should_run(self, responsible):
        return True

    @inlineCallbacks
    def apply_config(self, responsible, arg, modified_paths):
        """
        2 subscriptions: apply_config can be called twice during one apply.
        restart bind when :
        - network configuration change (network in CONFIG_DEPENDS =>
            modified_paths empty)
        - configuration of resolv is modified (resolv in CONFIG_DEPENDS =>
            modified_paths empty)
        - nuauth is used with an AD, when AD configuration is modified (callback
             on key 'nuauth_bind_dependency' => 'nuauth_bind' in modified_paths)

        ConfigServiceComponent.apply_config is overridden here because merging it is complex.
        It could however be merged, hence the TODO tag.
        """
        #TODO: see if can be merged with ConfigServiceComponent.apply_config
        del arg
        if responsible.storage.get('bind_configured'):
            return
        else:
            responsible.storage['bind_configured'] = True

        yield deferToThread(self.setEnabledOnBoot, True)

        should_restart, retemplate = self._should_restart_retemplate(responsible, modified_paths)
        if not should_restart:
            responsible.feedback(tr("Nothing to do"))
            return

        if not retemplate:
            yield deferToThread(self._stop_then_start, None)
            return

        global_nameservers = tuple(
                nameserver for nameserver in
                    (
                        self.config['resolv'].nameserver1,
                        self.config['resolv'].nameserver2
                    )
                if nameserver
            )

        forwarded_domains = yield self.getForwardedDomains(responsible, global_nameservers)

        template_variables = {
            'forwarders': global_nameservers,
            'forwarded_domains': forwarded_domains
            }

        yield deferToThread(self._stop_then_start, template_variables)

    @inlineCallbacks
    def getForwardedDomains(self, responsible, nameservers):
        nuauth = self.config['nuauth']
        if (not nuauth.isConfigured()) or (not nuauth.hasAD()):
            responsible.feedback(
                _FEEDBACK_CFG_SIMPLE,
                GLOBAL_SERVERS=", ".join(nameservers),
            )
            returnValue({})

        ad_domain, ad_controller_ip = nuauth.org.dns_domain, nuauth.org.controller_ip

        responsible.feedback(
            _FEEDBACK_CFG_AD,
            GLOBAL_SERVERS=", ".join(nameservers),
            AD_DOMAIN=ad_domain,
            AD_CONTROLLER=ad_controller_ip
            )

        forwarded_domains = yield deferToThread(
            self._getForwardedDomains,
            responsible,
            ad_domain,
            ad_controller_ip,
            nameservers
            )

        # convert {'domain': (IP('172.16.3.1'),)} to {'domain': ('172.16.3.1',)}
        for domain in forwarded_domains:
            forwarded_domains[domain] = map(unicode, forwarded_domains[domain])
            responsible.feedback(
                tr("DNS forwarders for domain %(domain)s: [%(domain_fwd)s]"),
                domain=domain,
                domain_fwd=forwarded_domains[domain],
                )
        returnValue(forwarded_domains)

    def _stop_then_start(self, template_variables):
        """template_variables can be None: that means templates be untouched"""
        context = Context.fromComponent(self)
        try:
            self.service_stop(context)
        except RunCommandError:
            self.error("Could not stop bind normally, killing named.")
            #explicitely ignoring return value
            runCommand(self, 'killall named'.split())
            runCommand(self, 'killall -9 named'.split())

        try:
            if template_variables is not None:
                self.generate_configfile(template_variables)
        finally:
            self.service_start(context)

    def _getForwardedDomains(
        self,
        responsible,
        ad_domain,
        ad_controller_ips,
        global_nameservers
        ):

        ns_ips = list(global_nameservers) #copy
        #append ips to global nameservers in this particular operation:
        to_resolve = set()
        helpers = set()
        for item in ad_controller_ips.split():
            try:
                ip = IP(item)
            except Exception:
                to_resolve.add(item)
                continue
            item = str(ip)
            helpers.add(item)
            ns_ips.append(item)

        if helpers and to_resolve:
            responsible.feedback(tr(
                "We can use [%s] to resolve [%s]" % (
                    ', '.join(helpers), ', '.join(to_resolve)
                    )
                ))

        try:
            resolved_ips = iterable2ipset(
                    self,
                    ad_controller_ips.split(),
                    ns_ips,
                    )
        except UnresolvableHost, err:
            if helpers:
                responsible.feedback(
                    _FEEDBACK_DNSERROR_W_HELPERS,
                    name=err.unresolvable,
                    dns_servers_list=', '.join(ns_ips),
                    dns_additionnal_list=', '.join(helpers),
                    )
            else:
                responsible.feedback(
                    _FEEDBACK_DNSERROR_WO_HELPERS,
                    name=err.unresolvable,
                    dns_servers_list=', '.join(ns_ips),
                    )
            raise DNSError("Unresolvable host: %s" % err.unresolvable)
        responsible.feedback(tr(
                    "Using [%(servers_ip)s] as forwarders for the DNS "
                    "zone %(dns_zone)s"
                    ),
                servers_ip=', '.join((unicode(item) for item in resolved_ips)),
                dns_zone=ad_domain
                )
        return {ad_domain: resolved_ips}

    def _should_restart_retemplate(self, responsible, modified_paths):
        if responsible.implies_full_reload():
            responsible.feedback(tr("Full reconfiguration."))
            return True, True

        nuauth_modified = any(
            ('nuauth' in path) or ('nuauth_bind' in path)
            for path in modified_paths)
        nuauth_modified |= responsible.isRestoring()
        if nuauth_modified and self.__ad_involved():
            responsible.feedback(tr("Using Active Directory triggers DNS reconfiguration."))
            return True, True

        if responsible.has_no_diff():
            responsible.feedback(tr(
                "Loaded from remote configuration, cannot compute differences"
                ))
            return True, True

        self.debug("Active Directory is not the cause of the name server rereading conf.")
#        if not self.__from_other_module(modified_paths):
#            return True, True

        #triggered by modification of module listed in CONFIG_DEPENDS
        if self.__resolv_modified():
            responsible.feedback(tr(
                "Changing domain names resolution values triggers DNS reconfiguration and service restart"
                ))
            return True, True

        self.debug("values not changed for domain name resolution.")
        if self.__network_modified():
            responsible.feedback(tr("Configuring networks triggers DNS service restart"))
            return True, False
        self.debug("values for network were not changed.")
        self.info("name server: no modification to handle.")

        return False, False

    def __from_other_module(self, modified_paths):
        return len(modified_paths) == 0

    def __ad_involved(self):
        return self.__nuauth_hasAD() or self.__nuauth_hadAD()

    def __config_changed(self, *path):
        try:
            old = self.core.config_manager.get(
                which_configuration='applied',
                *path
                )
        except (KeyError, ConfigError):
            old = None

        try:
            current = self.core.config_manager.get(*path)
        except (KeyError, ConfigError):
            current = None

        return old != current

    def __resolv_modified(self):
        return self.__config_changed('resolv')

    def __network_modified(self):
        return self.__config_changed('network')


    def save_config(self, message=None, context=None):
        pass
