#coding: utf-8
"""
Copyright (C) 2010-2011 EdenWall Technologies
"""

from __future__ import with_statement

from os.path import exists, join
from subprocess import PIPE, STDOUT
from twisted.internet.defer import inlineCallbacks

from ufwi_rpcd.backend.exceptions import ConfigError
from ufwi_rpcd.common import EDENWALL
from ufwi_rpcd.common.error import exceptionAsUnicode
from ufwi_rpcd.common.process import createProcess
from ufwi_rpcd.common.service_status_values import ServiceStatusValues
from ufwi_rpcd.core.context import Context

from ufwi_conf.backend.unix_service import ConfigServiceComponent
from ufwi_conf.backend.unix_service import runCommandAndCheck
from ufwi_conf.backend.unix_service import RunCommandError
from ufwi_conf.common.ha_statuses import PRIMARY, SECONDARY
from ufwi_conf.common.site2site_cfg import Site2SiteCfg, RSA
from ufwi_conf.common.site2site_cfg import CONNECTED, DISCONNECTED, PHASE1_OK

from .error import FingerprintNotFound, InvalidConfError

class Site2SiteComponent(ConfigServiceComponent):
    NAME = "site2site"
    MASTER_KEY = NAME
    VERSION = "1.0"

    REQUIRES = ('config', )

    INIT_SCRIPT = "ipsec"
    PIDFILE = "/var/run/pluto/pluto.pid"
    EXE_NAME = "pluto"

    ACLS = {
        'ha': set(('getHAMode',)),
    }

    ROLES = {
        'conf_read': set(('getConfig','vpnstates',)),
        'conf_write': set(('setConfig',)),
        'multisite_read': set(("status",)),
    }

    CONFIG_DEPENDS = ('network',)

    CREATE_FINGERPRINT = '/usr/share/ufwi_rpcd/scripts/conf_ipsec.sh'

    def __init__(self):
        ConfigServiceComponent.__init__(self)
        self.cfg = None
        self.FINGERPRINT_CREATED = None
        self.FINGERPRINT = None

    def init(self, core):
        var_dir = core.config.get('CORE', 'vardir')
        self.FINGERPRINT_CREATED = join(var_dir, 'ufwi_conf', 'FINGERPRINT_CREATED')
        self.createFingerprint()

        try:
            self.FINGERPRINT = self.getFingerprint()
        except Exception, err:
            msg = exceptionAsUnicode(err)
            self.critical("Can not read fingerprint : '%s'" % msg)

        ConfigServiceComponent.init(self, core)
        self.addConfFile('/etc/ipsec.conf', 'root:root', '0644') # fixed content
        # included (not copied) by /etc/ipsec.secrets which is filled createFingerprint
        self.addConfFile('/etc/ipsec.d/private/keys.conf', 'root:root', '0600')
        self.addConfFile('/etc/ha.d/resource.d/ipsec', 'root:root', '0755')

    def createFingerprint(self):
        """
        create fingerprint if needed
        """
        if not exists(self.FINGERPRINT_CREATED):
            self.info('Generate new authentication key')
            runCommandAndCheck(self, [self.CREATE_FINGERPRINT])
            open(self.FINGERPRINT_CREATED, 'a').close() # touch

    def getFingerprint(self):
        command =  "ipsec showhostkey --left".split()
        proc = createProcess(self, command, stdout=PIPE, stderr=STDOUT, locale=False)
        # FIXME: use communicateProcess() with a timeout
        outputs = proc.communicate() # stdout, stderr
        stdout = outputs[0]
        retcode = proc.wait()
        if retcode:
            raise RunCommandError(unicode(command), retcode, unicode(stdout))
        else:
            self.debug("Success : '%s'" % unicode(command))
            for line in stdout.split('\n'):
                if "leftrsa" not in line:
                    continue
                else:
                    return line.split('=')[1]

            raise FingerprintNotFound("Could not find fingerprint")

    def read_config(self, responsible, *args, **kwargs):
        self.cfg = self._read_config()

    def _read_config(self):
        try:
            serialized = self.core.config_manager.get(self.NAME)
            serialized['myfingerprint'] = self.FINGERPRINT
        except (ConfigError, KeyError):
            self.warning("Site-to-site VPN not configured, default values loaded")
            return Site2SiteCfg.defaultConf(myfingerprint=self.FINGERPRINT)
        else:
            return Site2SiteCfg.deserialize(serialized)

    @inlineCallbacks
    def apply_config(self, responsible, paths, arg=None):
        # FIXME don't restart all vpn when network is modified
        context = Context.fromComponent(self)

        # on secondary if vpn at least one vpn is active, ipsec is an ha ressource
        # if ipsec is an ha ressource, when starting heartbeat will start ipsec (ha
        # component depends on site2site component)

        ipsec_is_ha_ressource = False
        if EDENWALL:
            try:
                ha_type = yield self.core.callService(context, 'ha', 'getHAMode')
                ipsec_is_ha_ressource = ha_type in [PRIMARY, SECONDARY]
            except Exception, err:
                self.debug("can not read high availability status")
                self.writeError(err)

        enabled_on_boot = self.cfg.isVpnUsed() and not ipsec_is_ha_ressource
        self.service_setEnabledOnBoot(context, enabled_on_boot)

        if not self.cfg.isVpnUsed() or ipsec_is_ha_ressource:
            self.service_stop(context)

        self.generate_configfile(self.getTemplateVariables())

        if self.cfg.isVpnUsed():
            to_start = False
            if ipsec_is_ha_ressource:
                try:
                    line = open("/var/lib/ufwi_rpcd/ha_status").readline()
                    if line == "ACTIVE\n":
                        to_start = True
                except Exception:
                    pass
            else:  # ipsec is not HA resource.
                to_start = True
            if to_start:
                status = self.service_status(context)[1]
                if status == ServiceStatusValues.RUNNING:
                    self.service_reload(context)
                else:
                    self.service_restart(context)

    def getTemplateVariables(self):
        """
        self.cfg.serialize() can not be used here
        """
        template_variables = {}
        vpns = []

        template_variables['myfingerprint'] = self.cfg.myfingerprint
        template_variables['vpn_used'] = self.cfg.isVpnUsed()

        if self.cfg.vpns is not None:
            for vpn in self.cfg.vpns:
                raw = vpn.serialize()
                if vpn.keytype() == RSA:
                    raw['fingerprint'] = vpn.fingerprint.fingerprint
                vpns.append(raw)
        template_variables['vpns'] = vpns

        return template_variables

    def save_config(self, message, context):
        self.debug("Saving site-to-site VPN module configuration")
        serialized = self.cfg.serialize()
        serialized.pop('myfingerprint', None)

        with self.core.config_manager.begin(self, context) as cm:
            try:
                cm.delete(self.NAME)
            except ConfigError:
                pass

            cm.set(self.NAME, serialized)
            cm.commit(message)

    def get_ports(self):
        """
        override UnixServiceComponent
        """
        return [
            {'proto':'udp', 'port': 500}, # IKE negotiations
            {'proto':'esp'}, # ESP encryption and/or authentication
            {'proto':'udp', 'port': 4500},  # NAT-Traversal.
            # not used {'proto':'51'}, # AH packet-level authentication
        ]

    def vpnState(self, logs, vpn):
        PHASE1 = "ISAKMP SA established"
        PHASE2 = "IPsec SA established"
        state = DISCONNECTED
        vpn = "\"%s\"" % vpn
        for line in logs.split('\n'):
            if vpn in line and PHASE1 in line:
                state = PHASE1_OK
            if vpn in line and PHASE2 in line:
                state = CONNECTED
                break
        return state

    # Services
    def service_saveConfiguration(self, context, message):
        self.save_config(message, context)

    def service_getConfig(self, context):
        return self.cfg.serialize()

    def service_setConfig(self, context, serialized, message):
        """
        field 'myfingerprint' in serialized is ignored
        in order to update 'myfingerprint', create a new service which:
            - unlink self.FINGERPRINT_CREATED
            - call self.createFingerprint()
        """
        cfg = Site2SiteCfg.deserialize(serialized)
        ok, msg = cfg.isValidWithMsg()
        if ok:
            self.cfg = cfg
            self.save_config(message, context)
        else:
            raise InvalidConfError(msg)

    def service_vpnstates(self, context):
        """
        return a dict where keys are identifier and values are state
        possible values for state: DISCONNECTED, PHASE1_OK, CONNECTED
        """
        in_error = not exists("/var/run/pluto/pluto.ctl")

        if not in_error:
            command =  "ipsec whack --status".split()
            proc = createProcess(self, command, stdout=PIPE, stderr=PIPE, locale=False)
            stdout, stderr = proc.communicate()
            retcode = proc.wait()
            in_error = retcode != 0
            if in_error:
                self.error("'%s' - return code: '%s'\nstderr:\n%s\n\nstdout:\n%s" % (
                    unicode(command), retcode, stderr, stdout)
                    )

        result = {}
        if self.cfg.vpns is not None:
            for vpn in self.cfg.vpns:
                if in_error:
                    result[vpn.identifier] = DISCONNECTED
                else:
                    result[vpn.identifier] = self.vpnState(stdout, vpn.identifier)

        return result

    def service_reload(self, context):
        """ Reload the service: reload don't supported by init script """
        self.startstopManager("restart")

    def service_runtimeFiles(self, context):
        files = {
            'deleted': (
                '/etc/ipsec.secrets',
                self.FINGERPRINT_CREATED,
                ),
            'added' : (
                ('/etc/ipsec.secrets', 'secrets'),
                (self.FINGERPRINT_CREATED, 'empty'),
                )
        }
        return files

    def service_runtimeFilesModified(self, context):
        # nothing to do
        pass
