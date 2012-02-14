#coding: utf-8

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
"""

from __future__ import with_statement
import subprocess # TODO remove
from twisted.internet.threads import deferToThread
from twisted.internet.defer import inlineCallbacks, returnValue

from error import NuConfError, MAIL_BAD_CONFIGURATION
from ufwi_rpcd.common import tr
from ufwi_rpcd.backend.exceptions import ConfigError
from ufwi_rpcd.common import EDENWALL
from ufwi_rpcd.core.context import Context
from ufwi_conf.backend.unix_service import (
    ConfigServiceComponent,
    runCommandAndCheck,
    )
from ufwi_conf.common.antispam_cfg import AntispamConf
from ufwi_conf.common.contact_cfg import ContactConf
from ufwi_conf.common.mail_cfg import MailConf

#generated file
GENFILE_HUBBED_HOSTS = '/etc/exim4/hubbed_hosts'
# * relay_domain_in

#Static file
GENFILE_LOCAL_ACL_CONF = '/etc/exim4/local_acl.conf'
#

GENFILE_UPDATE_EXIM4_CONF_CONF = '/etc/exim4/update-exim4.conf.conf'
# * smarthost
# * dc_relay_domain: can be empty
# * dc_relay_nets: can be empty

#Static file
GENFILE_MACRODEFS = '/etc/exim4/conf.d/main/01_exim4-config_listmacrosdefs-local'
# references the 2 following local_acl_antispam.conf & local_acl_antivirus.conf

GENFILE_LOCAL_ACL_ANTISPAM = '/etc/exim4/local_acl_antispam.conf'

#generated file
GENFILE_LOCAL_ACL_ANTIVIRUS = '/etc/exim4/local_acl_antivirus.conf'
# * use_antivirus

GENFILE_MAILNAME = '/etc/mailname'

GEN_FILES = (
    GENFILE_HUBBED_HOSTS,
    GENFILE_LOCAL_ACL_CONF,
    GENFILE_MACRODEFS,
    GENFILE_LOCAL_ACL_ANTISPAM,
    GENFILE_LOCAL_ACL_ANTIVIRUS,
    GENFILE_MAILNAME,
    GENFILE_UPDATE_EXIM4_CONF_CONF,
)

class EximComponent(ConfigServiceComponent):
    """
    Manage the basic configuration of a exim mail server
    """
    NAME = "exim"
    VERSION = "1.0"

    PIDFILE = "/var/run/exim4/exim.pid"
    EXE_NAME = "exim4"
    INIT_SCRIPT = 'exim4'

    REQUIRES = ('config', 'ufwi_conf', 'hosts', 'hostname')
    if EDENWALL:
        REQUIRES += ('antispam', )

    # not used
    CONFIG = {}
    CONFIG_DEPENDS = frozenset(('antivirus', 'antispam', 'hostname', 'hosts'))

    ACLS = {
        'antispam': set(('getAntispamConfig',)),
        'antivirus': set(('use',)),
        'CORE': set(('hasComponent',)),
        'hostname': set(('getShortHostname',)),
        'hosts': set(('getFqdn',)),
    }

    ROLES = {
        'conf_read': set(('getMailConfig', 'status')),
        'conf_write': set(('setMailConfig',)),
    }

    check_relay_host = ConfigServiceComponent.check_ip_or_domain
    check_virus_scan = ConfigServiceComponent.check_boolean

    def __init__(self):
        self.config = None
        ConfigServiceComponent.__init__(self)

    def init(self, core):
        ConfigServiceComponent.init(self, core)
        for genfile in GEN_FILES:
            self.addConfFile(genfile, 'root:root', '0644')

    def read_config(self, responsible, *args, **kwargs):
        self.config = MailConf.defaultConf()

        try:
            serialized = self.core.config_manager.get(self.NAME)
        except ConfigError:
            self.debug("Not configured, defaults loaded.")
            return

        config = MailConf.deserialize(serialized)
        valid, error = config.isValidWithMsg()
        if valid:
            self.config = config
        else:
            self.error(
                "Component %s read incorrect values. Message was: %s" % (self.NAME, error)
                )

    def save_config(self, message, context):
        serialized = self.config.serialize()

        with self.core.config_manager.begin(self, context) as cm:
            try:
                cm.delete(self.NAME)
            except:
                pass
            cm.set(self.NAME, serialized)
            cm.commit(message)

    def should_run(self, responsible):
        return True

    @inlineCallbacks
    def genConfigFiles(self, responsible):
        templates_variables = {}
        for attr in MailConf.ATTRS:
            templates_variables[attr] = getattr(self.config, attr)

        context = Context.fromComponent(self)

        fqdn = yield self.core.callService(context, 'hosts', 'getFqdn')
        responsible.feedback(tr("Default FQDN is %(FQDN)s"), FQDN=fqdn)
        hostname = yield self.core.callService(
            context, 'hostname', 'getShortHostname'
            )
        responsible.feedback(
            tr("Default hostname is %(HOSTNAME)s"), HOSTNAME=hostname
            )

        templates_variables.update({'fqdn': fqdn, 'hostname': hostname})

        templates_variables.update(self._getrelayed())
        yield self.addAntispamConfig(context, templates_variables, responsible)
        self.generate_configfile(templates_variables)
        yield self.updateConf(responsible)

    def updateConf(self, responsible):
        yield deferToThread(runCommandAndCheck, self,
                            ("/usr/sbin/update-exim4.conf",))

    @inlineCallbacks
    def addAntispamConfig(self, context, templates_variables, responsible):
        try:
            serialized_antispam_cfg = yield self.core.callService(context,
                'antispam', 'getAntispamConfig')
            antispam_cfg = AntispamConf.deserialize(serialized_antispam_cfg)
        except Exception, err:
            self.writeError(err)
            responsible.feedback(tr("Unreadable antispam configuration"))
            use_antispam = False
        else:
            use_antispam = antispam_cfg.use_antispam

        if not use_antispam:
            templates_variables['use_antispam'] = False
            responsible.feedback(tr("Not configured as an antispam system."))
            return

        templates_variables['use_antispam'] = True
        responsible.feedback(tr("Configuring as an antispam system."))

        mark_spam_level = float(antispam_cfg.mark_spam_level)
        responsible.feedback(tr("Spam mark level: %(LEVEL)s"), LEVEL=mark_spam_level)
        templates_variables['mark_spam_level'] = int(10 * mark_spam_level)

        deny_spam_level = float(antispam_cfg.deny_spam_level)
        responsible.feedback(tr("Spam rejection level: %(LEVEL)s"), LEVEL=deny_spam_level)
        templates_variables['deny_spam_level'] = int(10 * deny_spam_level)

    def service_getrelayed(self, context):
        """
        pre-format relay_domains var
        """
        return self._getrelayed()

    def _getrelayed(self):
        dc_relay_domains = self.config.relay_domain_in
        dc_relay_nets = self.config.relay_net_out

        if not dc_relay_domains:
            dc_relay_domains = ''
        else:
            dc_relay_domains = \
                "'%s'" % ":".join((unicode(domain) for domain in dc_relay_domains))

        if not dc_relay_nets:
            dc_relay_nets = ''
        else:
            dc_relay_nets = \
                "'%s'" % ":".join((net.strNormal() for net in dc_relay_nets))
        return {
            'dc_relay_domains': dc_relay_domains,
            'dc_relay_nets': dc_relay_nets
        }

    def get_ports(self):
        ports = [ {'proto':'tcp', 'port': 25} ]
        return ports

    # services
    def service_getMailConfig(self, context):
        return self.config.serialize()

    def service_setMailConfig(self, context, serialized, message):
        config = MailConf.deserialize(serialized)
        if config.getReceivedSerialVersion() != 1:
            raise NuConfError(
                MAIL_BAD_CONFIGURATION,
                "Incompatible version: %s" % config.getReceivedSerialVersion()
                )
        valid, error = config.isValidWithMsg()
        if not valid:
            raise NuConfError(
                MAIL_BAD_CONFIGURATION,
                "'%s' failed : '%s'" % (valid, error)
                )

        self.config = config
        self.save_config(message, context)
        serialized = self.core.config_manager.get(self.NAME)

        defer = self.core.callService(context, 'CORE', 'hasComponent', 'antivirus')
        defer.addCallback(self._use_antivirus, context)
        defer.addErrback(self.writeError)
        return defer

    def _use_antivirus(self, has_component, context):
        if has_component:
            defer = self.core.callService(context, 'antivirus', 'use', self.NAME, self.config.use_antivirus)
            return defer
        else:
            self.debug('antivirus component not available')

    # Not used yet

    #def service_searchLogs(self, context, string):
    #    """
    #    Search the logs for the specified string
    #    """
    #    return deferToThread(self.search_log, string)

    #def search_log(self, string):
    #    return subprocess.Popen(["/usr/sbin/exigrep", string, '/var/log/exim4/mainlog'], stdout=subprocess.PIPE).communicate()[0]

    #def service_searchMailQueue(self, context, string):
    #    """
    #    Search the current mail queue for the specified string
    #    """
    #    return deferToThread(self.search_queue, string)

    #def search_queue(self, string):
    #    return subprocess.Popen(["/usr/sbin/exiqgrep",string], stdout=subprocess.PIPE).communicate()[0]

    def service_restart(self, context):
        self.manage_clamav(context)
        return ConfigServiceComponent.service_restart(self, context)

    def manage_clamav(self, context):
        if self.old_clamav_config == self.CONFIG['virus_scan']:
            return

        if self.old_clamav_config:
            self.core.callServiceSync(context, "Clamav", "decrementUsageCount")
        else:
            self.core.callServiceSync(context, "Clamav", "incrementUsageCount")

        self.old_clamav_config =  self.CONFIG['virus_scan']

    def service_start(self, context):
        if self.CONFIG['virus_scan']:
            self.core.callServiceSync(context, "Clamav", "decrementUsageCount")

        self.old_clamav_config = self.CONFIG['virus_scan']

        return ConfigServiceComponent.service_start(self, context)

    def service_stop(self, context):
        if self.old_clamav_config:
            self.core.callServiceSync(context, "Clamav", "decrementUsageCount")

        return ConfigServiceComponent.service_stop(self, context)

    #@inlineCallbacks
    #def service_status(self, context):
    #    ret = yield self.core.callService(context, 'contact', 'status')
    #    ret = (self.NAME, ret[1])
    #    returnValue(ret)
