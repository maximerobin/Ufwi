#coding: utf-8
"""
Copyright (C) 2008-2011 EdenWall Technologies
Written by Michael Scherer <m.scherer AT inl.fr>
           Feth Arezki <farezki AT edenwall.com>
           Pierre-Louis Bonicoli <plbonicoli AT edenwall.com>
           François Toussenel <ftoussenel AT edenwall.com>
           Victor Stinner <vstinner AT edenwall.com>

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

from errno import EACCES
from glob import glob
from nnd.client import Client as NNDClient
from os import chmod, close, mkdir, unlink, write
from os.path import exists, join
from shutil import copy, move
from subprocess import PIPE
from tempfile import mkstemp, NamedTemporaryFile
from time import sleep
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.threads import deferToThread
from twisted.python.failure import Failure
import re

from ufwi_rpcd.backend.exceptions import ConfigError
from ufwi_rpcd.backend import tr
from ufwi_rpcd.backend.process import runCommand, is_enabled_in_runit
from ufwi_rpcd.common.download import decodeFileContent
from ufwi_rpcd.common.error import exceptionAsUnicode, reraise
from ufwi_rpcd.common import EDENWALL
from ufwi_rpcd.common.radius_client import RadiusServer
from ufwi_rpcd.core.config.manager import modify_ext_conf
from ufwi_rpcd.core.context import Context
from ufwi_conf.backend.dnsutils import boolean_dig
from ufwi_conf.backend.nnd_instance import NND_SOCKET
from ufwi_conf.backend.net_ads import (
    ad_info,
    net_ads_keytab_command,
    net_ads_testjoin,
    )
from ufwi_conf.backend.unix_service import (
    ConfigServiceComponent,
    fix_strict_perms,
    runCommandAndCheck,
    RunCommandError,
    )
from ufwi_conf.common.ha_statuses import ENOHA, SECONDARY, PRIMARY
from ufwi_conf.common.netcfg import deserializeNetCfg
from ufwi_conf.common.user_dir import AD, KERBEROS, KERBEROS_AD, \
    LDAP, NND, NuauthCfg, RADIUS, SAME, NOT_CONFIGURED
from ufwi_conf.common.user_dir.protocols import getNetBiosName

from .ad_join import check_join, configureLocalSid, joinAd, saveLocalSid, \
    sambaRuntimeFiles, sambaRuntimeFilesModified

from .error import NO_CACHE_DIR, NuauthException, \
    NUAUTH_INVALID_CONF, UNABLE_TO_FETCH_KEYTAB, NNDError
from .kerberos import parseKeytab
from .ldapsearch_return_codes import LDAPSEARCH_RETURN_CODES
from .tests import canconnectnnd, test_user, test_group, test_auth


MASTER_KEY = 'nuauth'  # For config_manager.

_RADIUS_CONF = '/etc/pam_radius_auth.conf'
_PAM_NUAUTH_CONF = '/etc/pam.d/nuauth'
_SASL_NUAUTH_CONF = '/etc/sasl/nuauth.conf'
_NUAUTH_KRB5 = '/etc/nufw/nuauth.d/nuauth_krb5.conf'
_NUAUTH_USER_DIR_CONF = '/etc/nufw/nuauth.d/nuauth_user_dir.conf'
#Automatic fetching of keytab produces this file
_AD_KEYTAB = '/etc/krb5.keytab'
_NSSWITCH_CONF = '/etc/nsswitch.conf'

_SMB_CONF='/etc/samba/smb.conf'


_PAM_LDAP_CONF = '/etc/pam_ldap.conf'
_NSS_LDAP = '/etc/libnss-ldap.conf'
KRB5_KEYTAB_FILENAME = 'nuauth.keytab'
CACHE_DIR = '/var/cache/ufwi_rpcd'
ETC_DIR = '/etc/nufw'
CACHE_KRB5_KEYTAB_FILENAME = join(CACHE_DIR, KRB5_KEYTAB_FILENAME)
KRB5_KEYTAB_FILENAME = join(ETC_DIR, KRB5_KEYTAB_FILENAME)


_NND_EXE = "/usr/bin/nufw-nss-daemon"
_NND_CONF = "/etc/nnd/nnd.conf"
_NND_CA_DIR = "/etc/nnd/certs"
_CANAMEFORMAT = "CA_cert_%s.pem"
_NND_CONFCHECK_CMD = (_NND_EXE, "--testconf")
_NND_UP_TIMEOUT = 15 #seconds per server


LDAP_CERT_FILE = '/var/lib/ufwi_rpcd/ldap_server_cert'
LDAP_CERT_FILE = '/var/lib/ufwi_rpcd/ldap_server_cert'


TEST_LDAPCONF = '/var/lib/ufwi_rpcd/test_ldap/ldap.conf'
_LDAP_CONF = '/etc/ldap/ldap.conf'
LDAPSEARCH_BIN = '/usr/bin/ldapsearch'

_PAMTYPE = {
    AD: 'winbind',
    NND: 'ldap',
    LDAP: 'ldap',
    RADIUS: 'radius_auth',
    KERBEROS: 'krb5',
    KERBEROS_AD: 'winbind',
    NOT_CONFIGURED : ''
}

_LOG_NSS = '[NSS] '
_LOG_PAM = '[PAM] '

tech2user = {
    AD: "Active Directory",
    NND: "Generic LDAP",
    LDAP: "Posix LDAP",
    RADIUS: "Radius",
    KERBEROS: "Kerberos",
    KERBEROS_AD: "Active Directory with Kerberos support",
    NOT_CONFIGURED : "No Directory"
}

_INITIALIZING_GROUP_MAPPING_MSG = tr(
    "Initializing group mapping with a request on '%(USERNAME)s' info"
    )


def _nsswitch_compat(_type):
    if _type == AD:
        return 'winbind'
    if _type == LDAP:
        return 'ldap'

    return ''

def _cleandir(directory, globexpr):
    if exists(directory):
        for filename in glob(join(directory, globexpr)):
            unlink(filename)
    else:
        mkdir(directory)

def _gennames(prefix, base, number):
    """
    _gennames("domain", 1, 4)
    -> 'domain1'
    -> 'domain2'
    -> 'domain3'
    -> 'domain4'
    """
    for index in xrange(number):
        yield "%s%d" % (prefix, base + index)

def _nnddomainlabels(domains):
    return ",".join(
        _gennames("domain", 1, len(domains))
        )

def _nndserverlabels(domain_index, domain):
    return",".join(
        _gennames(
            "server%s." % domain_index,
            1,
            len(domain.servers)
            )
        )

def _nndsocketexists():
    if not exists(NND_SOCKET):
        raise NNDError("Socket does not exist: %s" % NND_SOCKET)
    return "ok"

class NuauthComponent(ConfigServiceComponent):
    """
    - services of ha & hostname:
        are called when determining netbios name during apply
    - service of resolv :
        nameserver1 is used during apply when trying to resolv
        kerberos names
    - nuauth calls ha.getHAMode() but it works if the component
      is not loaded
    """

    NAME = MASTER_KEY
    VERSION = "1.0"

    REQUIRES = ('hostname', 'resolv')

    CONFIG = {}

    CONFIG_DEPENDS = ('nuauth_bind',)

    ACLS = {
        'bind': set(('addForwarderDomain',)),
        'ha': set(('getHAMode', 'syncTime')),
        'hostname': set(('getPrimaryHostname',)),
        'network': set(('getNetconfig',)),
        'nuauth': set(('status','start')),
        'resolv': set(('addDomainNameServer', 'booleanQuery')),
        'nupki': set(('getPrivateCertPath', 'getCertPath', 'getCACertPath')),
        'system': set(('setUseNND',)),
        'ufwi_ruleset': set(('setConfig',)),

        # dummy acl just to be able to check that auth_cert component is loaded
        # (see _ufwi_rpcdStarted() method)
        'auth_cert': set(('status',)),
    }

    ROLES = {
        'conf_read': frozenset((
            'getNuauthConfig',
            'availableModules',
            'test_user',
            'test_group',
            'test_auth',
            'ad_info',
            )),
        'conf_write': frozenset((
            'setNuauthConfig',
            'upload_krb_keytab',
            'upload_ldap_server_cert',
            'delete_ldap_server_cert',
            'testLDAP',
            'testRADIUS'
            )),
        'multisite_read': set((
            'status',
        )),
    }

    check_ldap_ip = ConfigServiceComponent.check_ip
    check_ad_ip = ConfigServiceComponent.check_ip
    check_ad_domain = ConfigServiceComponent.check_domain
    check_ad_dns_domain = ConfigServiceComponent.check_domain

    def __init__(self):
        ConfigServiceComponent.__init__(self)
        self.__during_ha_import = False
        self.__config_before_ha_import = None
        self.config = None
        self.adstatus = False
        self.last_ad_info = {}
        self.has_auth_cert = False
        self.ad_status_update_time = "Not updated yet"

    def init(self, core):
        ConfigServiceComponent.init(self, core)

        try:
            if not exists('/etc/sasl'):
                mkdir('/etc/sasl')
            chmod('/etc/sasl', 0755)
        except OSError, err:
            if err.errno == EACCES:
                self.critical("SASL trouble ahead: %s" % err)
            else:
                raise

        # auth
        self.addConfFile(_PAM_NUAUTH_CONF, 'root:root', '0644')
        self.addConfFile(_PAM_LDAP_CONF, 'root:nuauth', '0644')
        self.addConfFile('/etc/krb5.conf', 'root:root', '0644')
        self.addConfFile(_SMB_CONF, 'root:root', '0644')
        ## radius
        self.addConfFile(_RADIUS_CONF, 'nuauth:nuauth', '0600')
        ## kerberos
        self.addConfFile(_SASL_NUAUTH_CONF, 'root:root', '0644')
        self.addConfFile(_NUAUTH_KRB5, 'root:root', '0644')

        # group
        ## generic
        self.addConfFile(_NSSWITCH_CONF, 'root:root', '0644')
        ## ldap
        self.addConfFile(_NSS_LDAP, 'root:root', '0644')
        self.addConfFile(_LDAP_CONF, 'root:root', '0644')
        ## nnd
        self.addConfFile(_NND_CONF, 'root:root', '0644')
        #ldap tests
        self.addConfFile(TEST_LDAPCONF, 'root:root', '0644')

        # auth & group
        ## ldap, ad, nnd
        self.addConfFile(_NUAUTH_USER_DIR_CONF, 'root:root', '0644')

        self.core.notify.connect('ha', 'ImportStart', self.__haImportStart)
        self.core.notify.connect('ha', 'ImportEnd', self.__haImportEnd)
        self.core.notify.connect('ufwi_rpcd', 'started', self._ufwi_rpcdStarted)

    def _ufwi_rpcdStarted(self, notify_context):
        context = Context.fromComponent(self)
        self.has_auth_cert = self.core.hasComponent(context, 'auth_cert')

    def getHostname(self):
        context = Context.fromComponent(self)
        return self.core.callService(context, "hostname",
            "getPrimaryHostname")

    def __haImportStart(self, context):
        self.__during_ha_import = True
        #save the config before we overwrite it!
        #This config will only be used to calculate if we should or not
        #attempt an AD join
        self.__config_before_ha_import = self.config.serialize()

    def __haImportEnd(self, context):
        self.__during_ha_import = False
        self.__config_before_ha_import = None

    def __previous_config(self):
        """
        Finds the running config or returns None
        """
        if self.__during_ha_import:
            return self.__config_before_ha_import
        try:
            return self.core.config_manager.get(
                self.NAME,
                which_configuration='applied'
                )
        except (KeyError, ConfigError):
            return None

    def _parameters_unchanged(self):
        previous_config = self.__previous_config()
        if previous_config is None:
            return False

        return self.config.serialize() == previous_config

    def apply_config(self, responsible, arg, modified_paths):
        """
        return a deferred
        """
        self.important("Nuauth module applying its config")
        #a deferred
        return self._apply_conf(responsible)

    def checkApply(self, data):
        if isinstance(data, Failure):
            self.critical("Problem configuring nuauth")
            self.writeError(data)
            # a rollback will be triggered
            return data

    def service_restartWinbind(self, context):
        #winbind will not stop when asked
        #We use runit for winbind, so...
        self.killwinbind()

    def killwinbind(self):
        command = '/usr/bin/killall -9 winbindd'
        process, status = runCommand(self, command.split(), env={})
        if status:
            self.info("winbind: no such process?")

    @inlineCallbacks
    def timedcheck(
        self,
        tries,
        function,
        func_args=(),
        func_kw=None,
        message="",
        err_message="",
        suc_message=""
        ):
        """
        tries: int > 1
        command: as a list
        """
        if func_kw is None:
            func_kw = {}

        last = tries - 1
        for time in xrange(tries):
            yield deferToThread(sleep, 1)
            try:
                if message:
                    self.debug(message)
                yield deferToThread(function, *func_args, **func_kw)
            except Exception:
                if err_message:
                    self.debug(err_message)

                if time == last:
                    raise
            else:
                if suc_message:
                    self.debug(suc_message)
                break

    @inlineCallbacks
    def _apply_conf(self, responsible):
        ###Ensure winbind is always startable (it was not beforehand)
        ###See commented calls in startServices/stopServices

        yield deferToThread(self.stopServices, responsible)

        ha_type = ENOHA
        if EDENWALL:
            context = Context.fromComponent(self)
            try:
                ha_type = yield self.core.callService(context, 'ha', 'getHAMode')
            except Exception, err:
                self.debug("can not read high availability status")
                self.writeError(err)

        yield self._config_nss(ha_type, responsible)

        yield self._config_pam(ha_type)

        yield deferToThread(self.startServices, responsible, ha_type)

    def stopService(self, name):
        self.info("Stop service %s" % name)
        try:
            self.etc_initd(name, "stop")
        except Exception, err:
            self.error('Stopping service %s failed: %s'
                       % (name, exceptionAsUnicode(err)))

    def stopRunit(self, name):
        self.info("Stop runit of service %s" % name)
        try:
            self.etc_initd(name, "exit")
        except Exception, err:
            self.error('Stopping runit of %s failed: %s'
                       % (name, exceptionAsUnicode(err)))

    def stopServices(self, responsible):
        responsible.feedback(tr("Stopping services"))
        self.etc_initd("nuauth", "stop")

        if is_enabled_in_runit("nufw-nss-daemon"):
            self.stopService("nufw-nss-daemon")
            # If we don't stop "runit nufw-nss-daemon" process, reenable
            # quickly nufw-nss-daemon in runit (create the symlink) may fail:
            # sometimes runit starts nufw-nss-daemon and then quickly stops it.
            # Stop runit ensures this weird behaviour.
            self.stopRunit("nufw-nss-daemon")
            self.set_enabled_in_runit(False, "nufw-nss-daemon")

        if is_enabled_in_runit('winbind'):
            self.stopService('winbind')
            self.set_enabled_in_runit(False, 'winbind')
        self.killwinbind()

    def startServices(self, responsible, ha_type):
        responsible.feedback(tr("Starting services"))

        if not self.has_auth_cert:
            self.etc_initd("nuauth", "start")
        else:
            self.debug("Don't start nuauth: auth_cert will restart the service")

    def _enable_winbind(self, ha_type):
        # if winbind is an ha ressource: when starting heartbeat will start winbind
        self.set_enabled_in_runit(True, 'winbind')
        self.killwinbind()
        try:  # In case it was already AD:
            self.etc_initd("winbind", "start")
        except RunCommandError:
            # The link has just been created (causes "runsv not running"),
            # in case we switch to AD.
            pass


    def etc_initd(self, daemon_name, action):
        """
        Sensible actions: start, stop, restart
        """
        cmd = "/etc/init.d/" + daemon_name, action
        try:
            runCommandAndCheck(self, cmd)
        except RunCommandError, err:
            self.error(
                "Action '%s' on daemon %s failed" %
                (action, daemon_name)
                )
            reraise(err)
        return True

    @inlineCallbacks
    def _config_pam(self, ha_type):
        auth_type = self.config.getAuthType()
        self.info(_LOG_PAM + "Configuring for protocol %s" % auth_type)

        self.generate_configfile({}, (_SASL_NUAUTH_CONF,))

        if not auth_type in (NOT_CONFIGURED, LDAP, NND, RADIUS, AD, KERBEROS,
         KERBEROS_AD):
            raise NotImplementedError("Unhandled auth protocol: %s" %
                self.config.org.protocol)

        yield self.configure_auth(auth_type, ha_type)

        pam_type = _PAMTYPE[auth_type]
        self.info("Nuauth pam type: %s" % pam_type)
        self.generate_configfile({'pam_type': pam_type}, (_PAM_NUAUTH_CONF,),
            prefix=_LOG_PAM)
        self.info(_LOG_PAM + "Done configuring for protocol %s" % auth_type)

    @inlineCallbacks
    def configure_auth(self, auth_type, ha_type):
        """
        Always generate all files (whatever the configuration), so unused
        files are cleaned.
        """
        yield self.configure_kerberos(auth_type, ha_type)
        self.configure_radius(auth_type)

    @inlineCallbacks
    def configure_kerberos(self, auth_type, ha_type):
        templates_variables = {}
        if auth_type == KERBEROS_AD:
            if self.config.org.dns_domain is None:
                raise NuauthException(NUAUTH_INVALID_CONF, "Unspecified domain")

            templates_variables.update({
                # AD
                'use_kerberos': True,
                'realm': self.config.org.domain.upper(),
                'domain': self.config.org.dns_domain,
                'kdc': self.config.org.controller_ip,
            })
        elif auth_type == KERBEROS:
            # Kerberos, main realm
            # they are all strings ! kerberos_domain, kdc
            templates_variables.update({
                'use_kerberos': True,
                'kdc': unicode(self.config.auth.kdc),
                'realm': unicode(self.config.auth.kerberos_domain).upper(),
                'domain': unicode(self.config.auth.kerberos_domain).lower(),
            })

        if templates_variables.get('use_kerberos', False):
            templates_variables['hostname'] = yield self.getHostname()

        self.generate_configfile(templates_variables, (_NUAUTH_KRB5, '/etc/krb5.conf',))

        if auth_type == KERBEROS:
            if exists(CACHE_KRB5_KEYTAB_FILENAME):
                #We are safe here:
                #from shutils.copy doc:
                #"Copy the file src to the file or directory dst." [...]
                #a file with the same basename as src is created
                #(or overwritten) in the directory specified. Permission bits
                #are copied. src and dst are path names given as strings.
                copy(CACHE_KRB5_KEYTAB_FILENAME, KRB5_KEYTAB_FILENAME)
                fix_strict_perms('root', 'nuauth', KRB5_KEYTAB_FILENAME)
        elif auth_type == KERBEROS_AD:
            if ha_type != SECONDARY:
                for keytab_command in ('create', 'add nuauth'):
                    try:
                        net_ads_keytab_command(self,
                            self.config.org.user,
                            self.config.org.password,
                            keytab_command)
                    except RunCommandError:
                        raise NuauthException(UNABLE_TO_FETCH_KEYTAB,
                            "[Kerberos+AD] Could not fetch AD keytab")

                move(_AD_KEYTAB, KRB5_KEYTAB_FILENAME)
                fix_strict_perms('root', 'nuauth', KRB5_KEYTAB_FILENAME)

    def configure_radius(self, auth_type):
        templates_variables = {
            'use_radius': auth_type == RADIUS,
            'radius_conf': self.config.auth
        }

        self.generate_configfile(templates_variables, (_RADIUS_CONF,),
            prefix=_LOG_PAM)

    def _pam_ldap(self):
        pass
        #everything done nss side

    def _pam_nnd(self):
        pass
        #everything done nss side

    @inlineCallbacks
    def _config_nss(self, ha_type, responsible):
        protocol = self.config.org.protocol

        self.info(_LOG_NSS + "Configuring for protocol %s" % protocol)

        self.critical(
            _LOG_NSS
            + "Now configuring nuauth directory source for protocol %s"
            % protocol
            )
        responsible.feedback(
            tr(
                "Now configuring nuauth group directory source for "
                "%(AUTH_PROTOCOL)s protocol."
            ),
            AUTH_PROTOCOL=tech2user[protocol]
            )
        if protocol == AD:
            passwd = group = 'files winbind'
            shadow = 'files'
        elif protocol == LDAP:
            passwd = group = shadow = 'files ldap'
        else:
            passwd = group = shadow = 'compat'
        self.generate_configfile(
            {
            'passwd': passwd,
            'group': group,
            'shadow': shadow,
            },
            (_NSSWITCH_CONF,),
            prefix=_LOG_NSS
        )

        use_nnd = (protocol == NND)

        ctx = Context.fromComponent(self)
        yield self.core.callService(ctx, 'system', 'setUseNND', use_nnd)

        config = {'nufw': {'require_group_name': use_nnd}}
        yield self.core.callService(ctx, 'ufwi_ruleset', 'setConfig', config)

        templates_variables = {}
        if protocol == NND:
            templates_variables['auth_module'] = 'nnd'
            templates_variables['groups_module'] = 'nnd'
            templates_variables['use_groups_name'] = 1
            templates_variables['log_users_without_realm'] = 0
        else:
            templates_variables['auth_module'] = 'system'
            templates_variables['groups_module'] = 'system'
            templates_variables['use_groups_name'] = 0
            templates_variables['log_users_without_realm'] = 1

        self.generate_configfile(templates_variables, (_NUAUTH_USER_DIR_CONF,), prefix=_LOG_NSS)

        if protocol == LDAP:
            self._nss_ldap(responsible)
        elif protocol == NND:
            yield self._nss_nnd(responsible)
        elif protocol == AD:
            yield self._nss_ad(ha_type, responsible)
        elif protocol == NOT_CONFIGURED:
            #/etc/nsswitch will contain 'compat' value
            pass
        else:
            responsible.feedback(tr("This protocol is not handled, sorry"))
            raise NotImplementedError(
                "Unhandled org protocol: %s" % protocol
                )
        self.info(_LOG_NSS + "Done configuring for protocol %s" % protocol)

    def _nss_ldap(self, responsible):
        if self.config.org.protocol != LDAP:
            return
        self.generate_configfile(
            {
                'user' : self.config.org.user,
                'password' : self.config.org.password,
                'dn_users' : self.config.org.dn_users,
                'dn_groups' : self.config.org.dn_groups,
                'uri': self.config.org.uri,
                'server_cert_set': self.config.getLdapCertPresent(),
                'reqcert': self.config.getReqcertPolicy(),
            },
            (
                _NSS_LDAP,
                _LDAP_CONF,
                _PAM_LDAP_CONF
            ),
            prefix=_LOG_NSS
            )

    @inlineCallbacks
    def _nss_nnd(self, responsible):
        # Sort the domain list by key (i.e. by name), so that nnd.conf
        # reflects the domain order displayed in the frontend (to make
        # nnd.conf easier to check).
        domains = list(self.config.org.domains.values())
        domains.sort()

        # The CA certificates will be (re)created below.
        _cleandir(_NND_CA_DIR, _CANAMEFORMAT % "*")

        serversnb = 0

        for domain_index, domain in enumerate(domains):
            onebased_dindex = domain_index + 1
            domain_strindex = "domain%d" % onebased_dindex
            if domain.label == self.config.org.default_domain:
                default_domain = domain_strindex
            domain.server_list = _nndserverlabels(onebased_dindex, domain)
            # CA certificates.
            for server_index, server in enumerate(domain.servers):
                serversnb += 1
                if server.ca_cert:
                    canamevalues = "%d.%d" % (onebased_dindex, server_index + 2)
                    filepath = join(_NND_CA_DIR, _CANAMEFORMAT % canamevalues)
                    ca_cert = decodeFileContent(server.ca_cert)
                    with open(filepath, "w") as fd:
                        fd.write(ca_cert)
                    server.ca_path = filepath

        nnd_config = {
            "default_domain": default_domain,
            "domain_list": _nnddomainlabels(domains),
            "domains": domains,
            "socket": NND_SOCKET,
            "log_level": "DEBUG",
            "ldap_log_level": 0,
            }

        self.generate_configfile(nnd_config, (_NND_CONF,), prefix=_LOG_NSS)

        yield self._checknndconffile()
        created = self.set_enabled_in_runit(True, "nufw-nss-daemon")
        if not created:
            self.etc_initd("nufw-nss-daemon", "restart")

        self.debug("Waiting for nufw-nss-daemon")
        yield self._checknndsocket(serversnb)
        yield self._checknndstatus(serversnb)

    @inlineCallbacks
    def _checknndsocket(self, serversnb):
        yield self.timedcheck(
            _NND_UP_TIMEOUT*serversnb,
            _nndsocketexists,
            message="Checking socket existence (%s)..." % NND_SOCKET,
            err_message="Socket does not exist.",
            suc_message="Socket found."
            )

    @inlineCallbacks
    def _checknndstatus(self, serversnb):
        client = NNDClient(logger=self)
        yield self.timedcheck(
            _NND_UP_TIMEOUT*serversnb,
            canconnectnnd,
            func_args=(client, NND_SOCKET),
            message="Trying to connect...",
            err_message="Connection failed.",
            suc_message="Connection sucessful."
            )

    @inlineCallbacks
    def _checknndconffile(self):
        try:
            yield deferToThread(runCommandAndCheck, self, _NND_CONFCHECK_CMD)
        except Exception:
            raise NNDError(tr("Error in generated nufw-nss-daemon config file"))

    def __should_join(self, responsible):
        if not self.__during_ha_import:
            responsible.feedback(
                tr("Not during an HA import, forcing AD join")
                )
            return True
        elif not self._parameters_unchanged():
            responsible.feedback(tr("Parameters changed, forcing AD join"))
            return True
        try:
            check_join(self, responsible)
        except NuauthException:
            responsible.feedback(tr("Forcing AD join"))
            return True
        responsible.feedback(
            tr("It seems that the domain has been joined already.")
            )
        return False

    @inlineCallbacks
    def _nss_ad(self, ha_type, responsible):
        """If secondary configuration files will be generated but don't
        do join"""
        hostname = yield self.getHostname()

        should_join = ha_type == SECONDARY or self.__should_join(responsible)
        if should_join:
            netbios_name = getNetBiosName(hostname)
            yield self._config_ad(self.config.org, netbios_name, ha_type,
                responsible)

        if ha_type == PRIMARY:
            responsible.feedback(tr(
                "Setting time on the passive member of the HA cluster."
                ))
            yield self.ha_time_sync()

    @inlineCallbacks
    def _config_ad(self, ad_config, hostname, ha_type, responsible):
        self.info(_LOG_NSS + "Setting up connexion Active directory domain")

        domain = ad_config.dns_domain
        if domain is None:
            raise NuauthException(NUAUTH_INVALID_CONF, "Unspecified domain")
        domain = domain.upper()

        if hostname is None:
            raise NuauthException(NUAUTH_INVALID_CONF, "Unspecified hostname")
        hostname = hostname.upper()

        user = ad_config.user
        password = ad_config.password

        # ha enabled: use only service ips
        # ha disabled: use all ips (which are service ips)
        serialized_net_cfg = yield self.core.callService(
            Context.fromComponent(self),
            'network', 'getNetconfig'
            )
        netcfg = deserializeNetCfg(serialized_net_cfg)

        ips_edw = set()
        for iface in netcfg.iterInterfaces():
            for net in iface.iterNets():
                if len(net.service_ip_addrs) != 0:
                    ips_edw |= net.service_ip_addrs

        templates_variables = {
            #AD
            'use_ad': True,
            'domain': domain,
            'controller_ip': ad_config.controller_ip,
            'workgroup': ad_config.workgroup,
            'wins_ip': ad_config.getWinsIP(),
            'password': password,
            'hostname': hostname,
            'ips_edw': ips_edw,
        }

        auth_type = self.config.getAuthType()
        if auth_type == KERBEROS:
            #Kerberos, main realm
            #they are all strings ! kerberos_domain, kdc
            templates_variables['use_kerberos'] = True
            templates_variables.update(self.config.auth.iter_attr_and_values())

        self.generate_configfile(
            templates_variables, (_SMB_CONF,), prefix=_LOG_NSS
            )

        if ha_type == SECONDARY:
            sambaRuntimeFilesModified(self)
            self.debug(
                "Secondary node: not joining the Active Directory domain %s"
                % domain
                )
            return

        responsible.feedback(
            tr("Now joining the Active Directory domain %(AD_DOMAIN)s"),
            AD_DOMAIN=domain
            )

        #This will raise Exceptions if appropriate:
        yield deferToThread(
            self.joinAd, user, domain, password, hostname, responsible
            )

        if auth_type == KERBEROS_AD:
            saveLocalSid(self)

        responsible.feedback(
            _INITIALIZING_GROUP_MAPPING_MSG, USERNAME=ad_config.user
            )

        yield deferToThread(self._enable_winbind, ha_type)

        yield self._checkadstatus(ad_config.user)

        check_join(self, responsible)

    @inlineCallbacks
    def _checkadstatus(self, aduser):

        yield self.timedcheck(
            20,
            runCommandAndCheck,
            func_args=(
                self, ["/usr/bin/wbinfo", "-i", aduser]
                )
            )

    def joinAd(self, user, domain, password, hostname, responsible):
        try:
            # FIXME: read the domain from the resolv component using a service
            # FIXME: call or use a component method
            our_dns_domain = self.core.config_manager.get('resolv', 'domain')
            if our_dns_domain is not None:
                our_dns_domain = our_dns_domain.lower()
            ad_dns = self.config.org.dns_domain
            if ad_dns is not None:
                ad_dns = ad_dns.lower()
            if ad_dns == our_dns_domain:
                block_tcp_53 = "no"
                responsible.feedback(
                    tr(
                        "Joining and registering our hostname '%(HOSTNAME)s' "
                        "in '%(DOMAIN)s' DNS record."
                        ),
                    HOSTNAME=hostname,
                    DOMAIN=our_dns_domain
                    )
            else:
                block_tcp_53 = "yes"
                responsible.feedback(
                    tr(
                        "Joining but NOT registering DNS record in domain "
                        "'%(AD_DOMAIN)s' because the domain of this server is "
                        "'%(DNS_DOMAIN)s'."
                    ),
                    DNS_DOMAIN=our_dns_domain,
                    AD_DOMAIN=ad_dns,
                )
        except ConfigError:
            block_tcp_53 = "no"
            responsible.feedback(
                tr(
                "Joining and trying to register the DNS record because the server "
                "domain is not set. This may explain a delay in joining the DNS record."
                )
            )
        #following line raises many exceptions, see the method joinAd
        self.important("May take time (several minutes)")
        return joinAd(self, user, domain, password, block_tcp_53)

    def read_config(self, *args, **kwargs):
        try:
            self.config = self._read_config()
        except (ConfigError, KeyError):
            self.debug("Nuauth: user directory config not loaded, nuauth not configured")
            server_cert_set = exists(LDAP_CERT_FILE)
            self.config = NuauthCfg()
            self.config.setLdapCertPresent(server_cert_set)

        ok, msg = self.config.isValidWithMsg()
        if not ok:
            self.error("nuauth read an invalid config: %s" % msg)

    def _read_config(self):
        serialized = self.core.config_manager.get(MASTER_KEY)
        return NuauthCfg.deserialize(serialized)

    def save_config(self, message, context=None):
        serialized = self.config.serialize()
        with self.core.config_manager.begin(self, context) as cm:
            try:
                cm.delete(MASTER_KEY)
            except ConfigError:
                pass
            try:
                cm.delete('nuauth_bind')
            except ConfigError:
                pass
            cm.set(MASTER_KEY, serialized)
            # Make nuauth:apply depend on bind:apply:
            cm.set('nuauth_bind', 'nuauth_bind_dependency', '1')
            cm.commit(message)

    def service_availableModules(self, context):
        return {
            'auth': (RADIUS, KERBEROS, KERBEROS_AD, SAME, NOT_CONFIGURED),
            'group': (LDAP, AD, NND, NOT_CONFIGURED)
            }

    def service_getNuauthConfig(self, context):
        return self.config.serialize()

    def service_setNuauthConfig(self, context, serialized, message):
        self.config = NuauthCfg.deserialize(serialized)
        ok, msg = self.config.isValidWithMsg(use_state=True)
        if ok:
            self.save_config(message, context)
        else:
            msg = "Got an invalid configuration: %s (%s/%s)" % (msg,
                self.config.auth.protocol, self.config.org.protocol)
            raise NuauthException(NUAUTH_INVALID_CONF, msg)

    def get_ports(self):
        return [ {'proto':'tcp', 'port': 4129}, ]

    # maybe use slapdn ?
    def check_dn(self, value):
        regexp = re.compile('[A-Za-z0-9.-]+=[^=]+')

        for i in value.split(','):
            if not regexp.match(i):
                return False
        return True

    def service_upload_ldap_server_cert(self, context, encoded_bin):
        return deferToThread(self._upload_ldap_server_cert, encoded_bin)

    def _upload_ldap_server_cert(self, encoded_bin):
        #TODO: translate opening errors into user understandable strings
        decoded_content = decodeFileContent(encoded_bin)
        tmpfile, tmpfilename = mkstemp()
        try:
            write(tmpfile, decoded_content)
        except Exception:
            unlink(tmpfilename)
            raise
        finally:
            close(tmpfile)

        #TODO: here, check the file

        #FIXME: IOErrors to NuauthException
        move(tmpfilename, LDAP_CERT_FILE)

        fix_strict_perms('root', 'nuauth', LDAP_CERT_FILE)

        self.config.setLdapCertPresent(True)
        return "Ok"

    def service_delete_ldap_server_cert(self, context):
        return deferToThread(self._delete_ldap_server_cert)

    def _delete_ldap_server_cert(self):
        unlink(LDAP_CERT_FILE)
        self.config.setLdapCertPresent(False)
        return "Ok"

    def service_upload_krb_keytab(self, context, encoded_bin):
        return deferToThread(self._upload_krb_keytab, encoded_bin)

    def _upload_krb_keytab(self, encoded_bin):
        #TODO: translate opening errors into user anderstandable strings
        decoded_content = decodeFileContent(encoded_bin)
        tmpfile, tmpfilename = mkstemp(suffix='.keytab')

        try:
            write(tmpfile, decoded_content)
        except Exception:
            unlink(tmpfilename)
            raise
        finally:
            close(tmpfile)

        try:
            user_info = parseKeytab(self, tmpfilename)
        except Exception, err:
            try:
                unlink(tmpfilename)
            except OSError:
                pass
            raise err

        try:
            move(tmpfilename, CACHE_KRB5_KEYTAB_FILENAME)
        except IOError, err:
            if not exists(CACHE_DIR):
                raise NuauthException(NO_CACHE_DIR, "%s does not exist !" % CACHE_DIR)
            raise err

        fix_strict_perms('root', 'nuauth', CACHE_KRB5_KEYTAB_FILENAME)

        return user_info

    def checKerberosServerInDNS(self, kerberos_config):
        ns_server = self.core.config_manager.get("resolv", "nameserver1")
        return all(
            boolean_dig(self, server=ns_server, query=host)
            for host in (
                kerberos_config.kdc,
                kerberos_config.kerberos_domain
                )
            )

    def service_testRADIUS(self, context, radius_server, user, password):
        radius_server = RadiusServer.deserialize(radius_server)
        ok, msg = radius_server.isValidWithMsg()
        if not ok:
            raise NuauthException(msg)

        return radius_server.test(self, user, password)

    def service_testLDAP(self, context, dc, base, uri, search_filter, password):
        templates_variables = {'reqcert': 'allow'}
        self.generate_configfile(templates_variables, (TEST_LDAPCONF,))

        #example of generated command:
        #ldapwhoami -x -w nupik \
        # -D cn=admin,dc=edenwall,dc=com \
        # -H ldap://tetram.inl.fr"
        cmd = [LDAPSEARCH_BIN, "-x"]
        cmdstr = '%s -x' % LDAPSEARCH_BIN
        if password:
            cmd.extend(('-w', password))
            cmdstr += ' -w %%%password%%%'
        if dc:
            cmd.extend(('-D', dc))
            cmdstr += ' -D %s' % dc
        if base:
            cmd.extend(('-b', base))
            cmdstr += ' -b %s' % base
        cmd.extend(('-H', uri))
        cmdstr += ' -H %s' % uri
        cmd.append(search_filter)
        cmdstr += ' %s' % search_filter

        env = {'LDAPCONF': TEST_LDAPCONF}
        self.debug("env: %s" % unicode(env))

        with NamedTemporaryFile(suffix='.ldapsearch.stdout') as stdout_file:
            process, value = runCommand(
                self,
                cmd, cmdstr=cmdstr,
                stdout=stdout_file, stderr=PIPE,
                env=env
                )
            if value != 0:
                info = process.stderr.read()
                error_title = tr("ldapsearch encountered the following error:")
                if not info:
                    info = ""
                if value in LDAPSEARCH_RETURN_CODES:
                    msg = LDAPSEARCH_RETURN_CODES[value]
                    msg = "%s\n%s\n%s" % (error_title, msg, info)
                    raise NuauthException(
                        NUAUTH_INVALID_CONF,
                        "%s\n%s" % (error_title, info)
                        )
                raise NuauthException(
                    NUAUTH_INVALID_CONF,
                    "%s\n%s" % (error_title, info)
                    )

            stdout_file.seek(0)
            return stdout_file.read()

    def service_runtimeFiles(self, context):
        files = {
            'deleted': (
                LDAP_CERT_FILE,
                KRB5_KEYTAB_FILENAME
                ),
            'added' : (
                (LDAP_CERT_FILE, 'cert'),
                (KRB5_KEYTAB_FILENAME, 'cert')
                )
        }

        # Kerberos AD with HA: backup local sid
        if self.should_copy_ad_info():
            sambaRuntimeFiles(self, files)
        return files

    def service_runtimeFilesModified(self, context):
        if self.should_copy_ad_info():
            configureLocalSid(self)
            sambaRuntimeFilesModified(self)

    def should_copy_ad_info(self):
        return EDENWALL and self.config.hasAD()

    @modify_ext_conf
    def service_copyPKI(self, context, pkiname, cname):
        CERT_DEST = ETC_DIR + '/server.crt'
        KEY_DEST = ETC_DIR + '/server.key'
        CRL_DEST = ETC_DIR + '/server.crl'
        CA_DEST = ETC_DIR + '/ca.crt'

        types = {
            'certificate': CERT_DEST,
            'key': KEY_DEST,
            'ca': CA_DEST,
            'crl': CRL_DEST,
        }

        paths = []
        def addPath(path):
            paths.append(path)
        def copyPKI(unused):
            try:
                for type_, path in (('certificate', paths[0]),
                                    ('key', paths[1]),
                                    ('ca', paths[2])):
                    dest = types[type_]
                    try:
                        with open(dest, 'w+b') as fd:
                            fd.write(open(path).read())
                    except IOError, err:
                        try:
                            self.error(context,
                                       tr('Nuauth: ') +
                                       tr('Error while copying certificates from an internal PKI: %s')
                                       % err)
                        except Exception:
                            self.error(context,
                                       tr('Nuauth: ') +
                                       tr('Error while copying certificates from an internal PKI.'))
                        return
            except IndexError:
                return False
            return True

        component_context = Context.fromComponent(self)
        defer = self.core.callService(component_context, 'nupki',
                                      'getCertPath', pkiname, cname)
        defer.addCallback(addPath)
        defer.addCallback(lambda x: self.core.callService(component_context,
                              'nupki', 'getPrivateCertPath', pkiname, cname))
        defer.addCallback(addPath)
        defer.addCallback(lambda x: self.core.callService(component_context,
                              'nupki', 'getCACertPath', pkiname))
        defer.addCallback(addPath)
        defer.addErrback(self.writeError)
        defer.addCallback(copyPKI)
        return defer


    def service_test_user(self, context, username):
        nnd = self.config.org.protocol == NND and self.config.auth.protocol == SAME
        return deferToThread(
            test_user,
            self,
            username,
            nnd=nnd
            )
    service_test_user.__doc__ = test_user.__doc__

    def service_test_group(self, context, groupname):
        nnd = self.config.org.protocol == NND
        return deferToThread(
            test_group,
            self,
            groupname,
            nnd=nnd
            )
    service_test_group.__doc__ = test_group.__doc__

    def service_test_auth(self, context, username, passwd):
        nnd = self.config.org.protocol == NND and self.config.auth.protocol == SAME
        return deferToThread(
            test_auth,
            self,
            username,
            passwd,
            nnd=nnd
            )
    service_test_auth.__doc__ = test_auth.__doc__

    def _update_adstatus(self):
        self.adstatus = net_ads_testjoin(self)
        if self.adstatus:
            self.last_ad_info = ad_info(self)
            self.ad_status_update_time = self.timestamp()

    def _build_ad_info(self):
        return {
            "service version": 1,
            "current status": self.adstatus,
            "realm": self.last_ad_info.get("Realm", ""),
            "time offset": self.last_ad_info.get("Server time offset", ""),
            "update time": self.ad_status_update_time,
            "parent server": self.last_ad_info.get("LDAP server name", ""),
            }

    @inlineCallbacks
    def service_ad_info(self, context, wanted_version=1):
        result = yield deferToThread(self.ad_info, wanted_version)
        returnValue(result)

    def ad_info(self, wanted_version):
        self._update_adstatus()
        return self._build_ad_info()


