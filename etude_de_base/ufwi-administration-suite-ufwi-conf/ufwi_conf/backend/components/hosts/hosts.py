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
from twisted.internet.defer import inlineCallbacks
from ufwi_rpcd.backend.exceptions import ConfigError
from ufwi_rpcd.common.service_status_values import ServiceStatusValues
from ufwi_rpcd.core.context import Context
from ufwi_conf.backend.unix_service import ConfigServiceComponent

class InvalidOperation(Exception):
    pass

class InvalidValue(Exception):
    pass


HOSTS_FILE = '/etc/hosts'

class HostsComponent(ConfigServiceComponent):
    NAME = "hosts"
    VERSION = "1.0"

    REQUIRES = ('config', 'hostname', 'resolv',)

    INIT_SCRIPT = "/bin/true"
    CONFIG = { 'hosts' : {} }
    CONFIG_DEPENDS = frozenset(('resolv','hostname'))

    ROLES = {
        'conf_read': set(('getFqdn', 'get_hosts')),
        'conf_write': set(('discoverHosts',)),
    }

    ACLS = {
        'hostname': set(('getShortHostname',)),
        'resolv': set(('getDomain',)),
       }

    DEFAULT_HOSTS = {
        '127.0.0.1' : 'localhost.localdomain localhost my.edenwall.com',
        '::1'       : 'ip6-localhost ip6-loopback',
        'fe00::0'   : 'ip6-localnet',
        'ff00::0'   : 'ip6-mcastprefix',
        'ff02::1'   : 'ip6-allnodes',
        'ff02::2'   : 'ip6-allrouters',
        'ff02::3'   : 'ip6-allhosts',
    }

    def __init__(self):
        ConfigServiceComponent.__init__(self)
        self.addConfFile(HOSTS_FILE, 'root:root', '0644')
        self.key_exists = False

    def init(self, core):
        ConfigServiceComponent.init(self, core)
        if not self.key_exists:
            self.useDefaultConf()

    @inlineCallbacks
    def read_config(self, *args, **kwargs):
        """
        return a defer
        """
        try:
            self.CONFIG = self.core.config_manager.get(self.NAME)
            self.key_exists = True
            yield self.update_hostname()
        except ConfigError:
            self.key_exists = False
            self.debug("use default configuration")
            yield self._discover_hosts()

    def apply_config(self, *args):
        """
        write conf file

        Callback for config manager
        """
        self.generate_configfile(self.CONFIG)

    def rollback_config(self, *args):
        """
        read_config called just before
        same as apply but commit and save default conf if current conf is empty
        """
        # FIXME must be done but not supported yet
        #if not self.key_exists:
        #    self.useDefaultConf()
        return self.apply_config(*args)

    def useDefaultConf(self):
        """
        commit & apply default conf
        """
        self.debug("take in account default configuration")
        ConfigServiceComponent.save_config(self, 'hosts : default configuration') # commit
        self.core.config_manager.signalAutoconf()                                 # apply

    @inlineCallbacks
    def update_hostname(self):
        """
        add 127.0.1.1 line

        must not failed, if error don't add line starting with "127.0.1.1" in
        configuration
        """
        try:
            context = Context.fromComponent(self)
            hostname = yield self.core.callService(context, 'hostname', 'getShortHostname')
            domain = yield self.core.callService(context, 'resolv', 'getDomain')
            self.change_hostname(hostname, domain)
        except Exception, err:
            # eat error
            self.writeError(err)

    def change_hostname(self, hostname, domain):
        self.CONFIG['hosts']['127.0.1.1'] = '%s.%s %s' % (hostname, domain, hostname)
        self.warning('Hostname is now %r, domain name is now %r' % (hostname, domain))

    # services
    def service_getFqdn(self, context):
        hosts = self.CONFIG['hosts']
        try:
            localhost = hosts['127.0.1.1']
        except KeyError:
            # 127.0.1.1 is not configured yet, fallback on 127.0.0.1
            # (fqdn is 'localhost.localdomain' by default)
            localhost = hosts['127.0.0.1']
        #see change_hostname for string structure
        return localhost.split()[0]

    def service_get_hosts(self, context):
        """
        Return the list of hosts from /etc/hosts
        {'10.0.0.1' : 'example.org server.example.org'}
        """
        #see change_hostname for string structure
        return self.CONFIG['hosts']

    def service_discoverHosts(self, context):
        """ Discover the hosts file of the computer """
        return self._discover_hosts()

    @inlineCallbacks
    def _discover_hosts(self):
        """
        defaults and /etc/hosts

        if host are in /etc/hosts and default, /etc/hosts overwrite default
        """
        self.CONFIG['hosts'].clear()
        self.CONFIG['hosts'].update(self.DEFAULT_HOSTS)

        hosts = open(HOSTS_FILE)
        for l in hosts.readlines():
            l = l[:-1]
            l.strip()
            if '#' in l:
                l = l.split('#')[0]
            token = l.split()
            if len(token) < 2:
                continue
            name = token[0]
            if not name in self.CONFIG['hosts']:
                self.CONFIG['hosts'][name] = ''

            merged_hosts = self.CONFIG['hosts'][name].split(' ')
            for host in token[1:]:
                if host not in merged_hosts:
                    merged_hosts.append(host)

            if merged_hosts:
                self.CONFIG['hosts'][name] = ' '.join(merged_hosts)
        yield self.update_hostname()

    def service_status(self, context):
        """Implementation compulsory as we inherit of UnixServiceComponent"""
        return self.NAME, ServiceStatusValues.NOT_A_SERVICE

