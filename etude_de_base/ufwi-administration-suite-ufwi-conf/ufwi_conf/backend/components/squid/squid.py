# -*- coding: utf-8 -*-
"""
Copyright (C) 2007-2011 EdenWall Technologies
Written by Michael Scherer <m.scherer AT inl.fr>
           Francois Toussenel <ftoussenel AT edenwall.com>

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

from logging import debug
import os
import re

from twisted.internet.defer import inlineCallbacks

from ufwi_rpcd.backend.exceptions import ConfigError
from ufwi_rpcd.common.process import createProcess
from ufwi_rpcd.common.service_status_values import ServiceStatusValues
from ufwi_rpcd.core.context import Context
from ufwi_rpcd.core.config.manager import modify_ext_conf

from ufwi_ruleset.localfw.wrapper import LocalFW

from ufwi_conf.backend.unix_service import (
    ConfigServiceComponent, runCommandAndCheck)
from ufwi_conf.common.squid_cfg import SquidConf
from .error import NuConfError
from .error import SQUIDGUARD_COMPILE_ERROR

SQUIDGUARD_CONFIG = '/etc/squid/squidGuard.conf'
SQUID_AUTHORIZED_IP = '/var/lib/squidguard/db/good.iplist'
SQUID_GID_LIST = '/etc/edenwall/squid_authorized_gid.list'
COMPILE_SELECTED_CATEGORIES = "/etc/squid/compile_selected_categories"

SQUIDGUARD_DB_DIR = "/var/lib/squidguard/db"
BLACKLIST_GLOBAL_USAGE = SQUIDGUARD_DB_DIR + '/blacklists/global_usage'
CUSTOM_DIR = SQUIDGUARD_DB_DIR + '/custom'

NAME_RE = re.compile(r"^NAME:\s*(.*)")

def utf8_to_unicode_none_proof(text):
    """Accept None and non-ASCII strings."""
    try:
        return unicode(text, "utf-8")
    except TypeError:
        return u""

def text2list(text):
    from StringIO import StringIO
    return [line.strip() for line in StringIO(text).readlines()]

class ListFile:
    def __init__(self, path):
        self._path = path
        self.__list = set()
        self.__load()

    def __load(self):
        try:
            f = open(self._path)
        except IOError:
            return
        for i in f.readlines():
            # chomp
            i = i[:-1]
            self.__list.add(i)

    def save(self):
        f = open(self._path, "w+")
        for i in self.__list:
            f.write(i + '\n')
        f.close()

    def add(self, item):
        self.__list.add(item)
        self.save()

    def remove(self, item):
        self.__list.discard(item)
        self.save()

    def get(self):
        # return a copy
        return [x for x in self.__list]

    def clear(self):
        self.__list = set()
        self.save()

class SquidGuardConfigfile:

    def __init__(self, path):
        self._path = path
        self.__used = []
        self.__parse_file()

    # very light parser, i do not intend to support everything
    def __parse_file(self):

        f = open(self._path)
        for l in f.readlines():
            l = l.strip()
            if not l.startswith("pass custom_whitelist !custom_blacklist"):
                continue
            for a in l.split(' ')[3:]:
                if a[0] == '!':
                    self.__used.append(a[1:])
        # separer par les ' '
        # voir si il y a un ! ou pas
    def dump_list(self):
        debug(self.__used)

    def is_used(self, blacklist):
        return blacklist in self.__used


def setServiceEnabledOnBoot(context, init_script, enabled, S=20, K=None,
                            rcS=None):
    """ Useful when handling other services than the component's
    self.INIT_SCRIPT (e.g. havp in squid component).
    """

    if K is None:
        K = S
    if enabled:
        return runCommandAndCheck(
            context, ['/usr/sbin/update-rc.d', '-f', init_script, 'defaults',
                      unicode(S), unicode(K)])
    else:
        return runCommandAndCheck(context, ['/usr/sbin/update-rc.d', '-f',
                                            init_script, 'remove'])


class SquidComponent(ConfigServiceComponent):
    """
    Manage a Squid server, and can be used to modify squidguard blacklist
    """
    NAME = "squid"
    MASTER_KEY = NAME
    VERSION = "1.0"

    INIT_SCRIPT = "squid"

    PIDFILE = "/var/run/squid.pid"
    CONFIG_DEPENDS = ()

    ACLS = {
        'localfw': set(('addNatIptable', 'apply', 'clear', 'close', 'open')),
        'network': set(('getNetconfig',)),
        'ufwi_ruleset': set(('open', 'reapplyLastRuleset',)),
    }

    ROLES = {
        'conf_read': set((
                'getAvailableCategories',
                'getCustomBlacklist',
                'getCustomWhitelist',
                'getSquidConfig',
                'runtimeFiles')),
        'conf_write': set((
                'setCustomBlacklist',
                'setCustomWhitelist',
                'setSquidConfig')),
    }

    def get_ports(self):
        return [{'proto': 'tcp',
                 'port': 3128},]

    def init(self, core):
        ConfigServiceComponent.init(self, core)
        self.core = core
        self.addConfFile('/etc/havp/havp.config', 'root:root', '0644')
        self.addConfFile('/etc/squid/squid.conf', 'root:root', '0600')
        self.addConfFile('/var/lib/squidguard/db/good.iplist', 'root:root',
                         '0600')
        self.addConfFile('/var/www/proxy/blocked.php', 'root:root', '0644')
        self.addConfFile('/etc/squid/squidGuard.conf', 'root:root', '0644')
        self.addConfFile(COMPILE_SELECTED_CATEGORIES, 'root:root', '0755')
        for conf_file in (
            CUSTOM_DIR + '/blacklist.domains',
            CUSTOM_DIR + '/blacklist.urls',
            CUSTOM_DIR + '/whitelist.domains',
            CUSTOM_DIR + '/whitelist.urls'):
            self.addConfFile(conf_file, 'proxy:proxy', '0600')
        self.squid_dir = os.path.join(self.core.config.get('CORE', 'vardir'),
                                      'squid')
        if not os.path.exists(self.squid_dir):
            self.error(
                "The proxy directory `%s' did not exist.  Creating it." %
                self.squid_dir)
            try:
                os.mkdir(self.squid_dir)
            except OSError, err:
                self.error(
                    "Could not create the proxy directory `%s': %s" %
                    (self.squid_dir, err))
        if not os.path.exists(CUSTOM_DIR):
            try:
                os.mkdir(CUSTOM_DIR)
                # Chown it to proxy:proxy:
                os.chown(CUSTOM_DIR, 13, 13)
            except OSError, err:
                self.error(
                    "Could not create the custom blacklist directory `%s': %s"
                    % (CUSTOM_DIR, err))
        self.custom_blacklist_source = os.path.join(self.squid_dir,
                                                    'custom_blacklist_source')
        self.custom_whitelist_source = os.path.join(self.squid_dir,
                                                    'custom_whitelist_source')


    def read_config(self, *args, **kwargs):
        try:
            serialized = self.core.config_manager.get('squid')
        except (ConfigError, KeyError):
            self.squid_cfg = SquidConf()
        else:
            self.squid_cfg = SquidConf.deserialize(serialized)

    @inlineCallbacks
    def apply_config(self, *unused):
        """ Special case of apply_config: 2 services to handle: self (squid)
        and havp. """

        self.read_config()
        (custom_blacklist_domains, custom_blacklist_urls) = \
            self.dispatch_addresses(text2list(self.get_custom_blacklist()))
        (custom_whitelist_domains, custom_whitelist_urls) = \
            self.dispatch_addresses(text2list(self.get_custom_whitelist()))
        context = Context.fromComponent(self)

        try:
            if not self.squid_cfg.enabled:
                self.service_stop(context)
            if not (self.squid_cfg.enabled and
                    self.squid_cfg.antivirus_enabled):
                self.havp_stop()
                # Cannot use unix_service.setEnabledOnBoot here because we are not
                # enabling squid but havp.
                setServiceEnabledOnBoot(self, u"havp", False)
            else:
                setServiceEnabledOnBoot(self, u"havp", True)
            self.generate_configfile({
                    'conf': self.squid_cfg,
                    'custom_blacklist_domains': custom_blacklist_domains,
                    'custom_blacklist_urls': custom_blacklist_urls,
                    'custom_whitelist_domains': custom_whitelist_domains,
                    'custom_whitelist_urls': custom_whitelist_urls,
                    'squidguard_conf_dests': self._squidguard_conf_dests()})
            self.service_setEnabledOnBoot(context, self.squid_cfg.enabled,
                                          S=30, K=30)
            if self.squid_cfg.blacklist_enabled:
                if not self.compile_squidguard_base():
                    raise NuConfError(
                        SQUIDGUARD_COMPILE_ERROR,
                        "Could not take blacklist into account.")
            # Restart HAVP:
            if self.squid_cfg.enabled and self.squid_cfg.antivirus_enabled:
                self.havp_restart()
            # Reload or restart squid:
            if self.squid_cfg.enabled:
                status = self.service_status(context)[1]
                if status == ServiceStatusValues.RUNNING:
                    self.service_reload(context)
                else:
                    self.service_restart(context)
        except Exception:
            if self.squid_cfg.enabled:
                self.service_restart(context)
            raise

        localfw = LocalFW('transparent_proxy')
        if self.squid_cfg.transparent and self.squid_cfg.enabled:
            for ip in self.squid_cfg.authorized_ips:
                localfw.call('addNatIptable', False,
                    '-I PREROUTING -p tcp --dport 80 -s %s -j REDIRECT --to-ports 3128' % ip)
        # else: just clear existing rules
        context = Context.fromComponent(self)
        try:
            yield localfw.execute(self.core, context)
        except Exception, err:
            self.writeError(err,
                'Error while handling firewall NAT rules for the transparent proxy')
            raise

    def save_config(self, message, context=None):
        with self.core.config_manager.begin(self, context) as cm:
            try:
                cm.delete(self.MASTER_KEY)
            except ConfigError:
                pass
            cm.set(self.MASTER_KEY, self.squid_cfg.serialize())
            cm.commit(message)

    # Module-specific methods:

    def compile_squidguard_base(self):
        # Return True in case of success.
        # Always compile custom lists.
        ret_value = True
        for color in ("black", "white"):
            for type_ in ("domains", "urls"):
                process = createProcess(
                    self, ['/usr/bin/squidGuard', '-C',
                           "custom/%slist.%s" % (color, type_)])
                if process.wait() != 0:
                    return False
        # Compile other lists only if the compiled version is absent or older
        # than the source.
        process = createProcess(self, [COMPILE_SELECTED_CATEGORIES])
        if process.wait() != 0:
            ret_value = False

        process = createProcess(self, ['/bin/chown', '-R', 'proxy',
                                       SQUIDGUARD_DB_DIR])
        if process.wait() != 0:
            return False
        return ret_value

    def dispatch_addresses(self, addresses):
        """Return a tuple of lists (domains, urls), from a list of addresses.
        """
        domains = []
        urls = []
        address_re = re.compile(
            r'^(?P<proto>[a-zA-Z]*:)?/*(?P<domain>[^/]+)/*(?P<rest>.*)')
        for address in addresses:
            m = address_re.search(address)
            if m:
                if m.group('rest'):
                    urls.append(u'%s/%s' % (
                            utf8_to_unicode_none_proof(m.group('domain')),
                            utf8_to_unicode_none_proof(m.group('rest'))))
                else:
                    domains.append(utf8_to_unicode_none_proof(
                            m.group('domain')))
        return (domains, urls)

    def get_available_categories(self):
        """Return categories as a dict of dicts.
        See documentation of service_getAvailableCategories.
        """
        try:
            with open(BLACKLIST_GLOBAL_USAGE) as fd:
                categories = self.parse_global_usage(fd.readlines())
        except Exception, err:
            self.error(
                'Could not get blacklists categories from file %s (%s).' %
                (BLACKLIST_GLOBAL_USAGE, err))
            return {}
        return categories

    def get_custom_blacklist(self):
        return self.get_custom_list(self.custom_blacklist_source)

    def get_custom_list(self, filename):
        try:
            with open(filename) as fd:
                return fd.read()
        except Exception, err:
            if os.path.exists(filename):
                self.critical(
                    "Could not read custom blacklist from file `%s' (%s)." %
                    (filename, err))
        return ''

    def get_custom_whitelist(self):
        return self.get_custom_list(self.custom_whitelist_source)

    def havp_restart(self):
        runCommandAndCheck(self, ["/etc/init.d/havp", "restart"])

    def havp_stop(self):
        try:
            runCommandAndCheck(self, ["/etc/init.d/havp", "stop"])
        except Exception, err:
            self.error("Error while stopping havp (%s)." % err)

    def parse_global_usage(self, lines):
        """Return categories as a dict of dicts.
        See documentation of service_getAvailableCategories.
        """
        categories = {}
        def new_category():
            return {
                'DEFAULT_TYPE': u'black',
                'DESC EN': u'',
                'DESC FR': u'',
                'NAME EN': u'',
                'NAME FR': u''}
        category = new_category()
        name = ''
        for line in lines:
            m = NAME_RE.search(line)
            if m:
                if name:
                    categories[name] = category
                try:
                    name = m.group(1).strip()
                except Exception:
                    continue
                category = new_category()
            else:
                for field_name in category.keys():
                    start = field_name + ':'
                    if line.startswith(start):
                        try:
                            category[field_name] = unicode(
                                line[len(start)+1:].strip(), 'utf-8')
                        except Exception:
                            pass
                        continue
        if name:
            categories[name] = category
        return categories

    def set_custom_list(self, filename, text):
        with open(filename, 'w') as fd:
            fd.write(text)

    def _squidguard_conf_dests(self):
        result = []
        for (category_name, category) in self.get_available_categories().items():
            dest = {"name": category_name, "files": []}
            for type_ in ("domain", "expression", "url"):
                if os.path.exists(SQUIDGUARD_DB_DIR + "/blacklists/%s/%ss" %
                                  (category_name, type_)):
                    dest["files"].append("%slist blacklists/%s/%ss" % (
                            type_, category_name, type_))
            result.append(dest)
        return result


    # Services:

    def service_getAvailableCategories(self, context):
        """Return a dict of dicts (blacklists and whitelists combined).

        Example: {'gambling':
                      {'DEFAULT_TYPE': 'black',
                       'DESC EN': 'Gambling and games sites, casino, etc.',
                       'DESC FR': 'Sites de jeux en ligne, casino, etc.',
                       'NAME EN': 'Gambling/Casino games',
                       'NAME FR': 'Jeux casino'},
                  'cleaning':
                      {'DEFAULT_TYPE': 'white',
                       'DESC EN': 'Sites to disinfect, update and protect computers.',
                       'DESC FR': 'Sites pour désinfecter et mettre à jour des ordinateurs.',
                       'NAME EN': 'Cleanup, Antivirus etc',
                       'NAME FR': 'Nettoyage, Antivirus, etc'}}
        """
        return self.get_available_categories()

    def service_getCustomBlacklist(self, context):
        return self.get_custom_blacklist()

    def service_getCustomWhitelist(self, context):
        return self.get_custom_whitelist()

    def service_getSquidConfig(self, context):
        return self.squid_cfg.serialize()

    def service_runtimeFiles(self, context):
        return {'added': [(self.custom_blacklist_source, 'text'),
                          (self.custom_whitelist_source, 'text')],
                "deleted": (self.custom_blacklist_source,
                            self.custom_whitelist_source)}

    def service_runtimeFilesModified(self, context):
        pass

    @modify_ext_conf
    def service_setCustomBlacklist(self, context, text):
        self.set_custom_list(self.custom_blacklist_source, text)

    @modify_ext_conf
    def service_setCustomWhitelist(self, context, text):
        self.set_custom_list(self.custom_whitelist_source, text)

    def service_setSquidConfig(self, context, serialized, message):
        self.squid_cfg = SquidConf.deserialize(serialized)
        self.save_config(message, context)

