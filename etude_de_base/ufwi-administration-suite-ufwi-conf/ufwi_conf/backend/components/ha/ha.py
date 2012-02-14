#coding: utf-8
"""
Copyright (C) 2010-2011 EdenWall Technologies

Instance HAComponent have one member ha. This member is instancied in createHA().
ha member can be PrimaryHost or SecondaryHost:
    Implementation of PrimaryHost is inside ha/primary_host.
    Implementation of SecondaryHost is inside ha/secondary_host.
    PrimaryHost have member secondary of type Secondary defined in ha/primary/secondary.py.
    SecondaryHost have member primary of type Primary defined in ha/secondary/primary.py.

Most service calls are proxied to the PrimaryHost or SecondaryHost class.

service_callRemote is used in order to do remote call (from primary to secondary or vice versa)

Creation of link between primary and secondary
==============================================

- configureHA() must be called first on secondary and next on primary. It's
like setConfig (save step) and apply_config (apply step) will be called next.

- createHA() : called when ufwi_rpcd start if state is not ENOHA or when
    state is modified and during apply.
    - create needed iptables rules (8443, 54322, 54323 on dedicated ha interface)

- startHA() must be called on primary and here what is done by startHA():
    Primary                             Secondary
    5.0.0.1:54322 -------------------------> 5.0.0.2:54323
                                           |
       result <-----------------------------


Details about creation of link between primary and secondary
============================================================

User: connect to EDW2 with EAS
and configure HA in HA page
|-click on save button ---> ha.configureHA(...)
|-click on apply button---> apply_config(...)

User: connect to EDW1 with EAS
and configure HA in HA page
|-click on save button ---> ha.configureHA(...)
|-click on apply button---> apply_config(...)

User: connect to EDW1 with EAS
click on join button in HA page

ha.startHA() :

EdenWall 1 (future Primary)         |  EdenWall 2 (future Secondary)
------------------------------------|---------------------------------------
                                    |
 * ha.startHA()
 * self.start()
   (re)start heartbeat
 * createHA()
   calls to multisite_transport component:
   start(), setSelf(PRIMARY), setSelf(SECONDARY)
 * calls to localfw
 * calls to multisite_transport component:
   addRemote(PRIMARY), addRemote(SECONDARY)

 * register_firewall() -------------+-> ha.register(date)
                         register   |
                                    | * ntp.setDate()
                                    | * calls to multisite_transport component:
                                    |   setSelf(), addRemote(), start()
        end_registration            | * ha.setState(SECONDARY)
 <----------------------------------+-/
  |
  |                             |->-| * hello are scheduled here, but the first
  |                             |   |   hello won't be issued until secondary state is
  |                             ^   |   reached.
  |                             |   |
  |                             |
  |                             |          result of end_registration
 * ha.end_registration()        ------<------------<----------------<------------\
 * ha.setState(PRIMARY)                                                          |
 * config.apply()                                                                |
   doesn't trigger a configuration synchronisation on the secondary because      |
   nothing connected to event configModified)                                    ^
 * calls hb_takeover all                                                         |
 * syncConfig()                                                                  |
 * nurestore.duplicate()                                                         |
 * multisite_transport.hostFile() --+-> ha.setConfig()                           |
                                    | * multisite_transport.getFile()            |
                                    | * nurestore.import()                       ^
                                    | * filesModified()                          |
                                    |   For each component in components calls   |
                                    |   component.runtimeFilesModified().        |
                                    |   config.runtimeFilesModified() is called  |
                                    |   first and calls config.apply(): so state |
                                    |   SECONDARY is applied.                    |
                                    \--------------->------------>---------------/


How modifications are pushed from primary to secondary
======================================================

TODO


Hello
=====

Hello is triggered by EDW2.
-----------> ha.hello()
                 | **ON EDW1**
                 |-syncConfig()
                 |-components = nurestore.duplicate()
                 |-multisite_transport.hostFile()
                 |--> **ON EDW2**
                        ha.setConfig()
                          |-multisite_transport.getFile()
                          |-nurestore.import()
                          |-filesModified()
                          | For each component in components
                          | calls component.runtimeFilesModified()
                          | NB : config.runtimeFilesModified() is
                          | called first and calls config.apply() : so
                          | state SECONDARY is applied.
                 <--------|
"""

from __future__ import with_statement
from datetime import datetime
from M2Crypto.Rand import rand_bytes
from os import unlink
from os.path import exists, join
from threading import Lock
from subprocess import PIPE, STDOUT

from twisted.internet.defer import inlineCallbacks, returnValue, succeed
from twisted.internet.threads import deferToThread

from ufwi_rpcd.backend import tr
from ufwi_rpcd.backend.cron import scheduleOnce, scheduleRepeat
from ufwi_rpcd.backend.error import AclError
from ufwi_rpcd.backend.exceptions import ConfigError
from ufwi_rpcd.backend.process import runCommand, DEFAULT_TIMEOUT
from ufwi_rpcd.common.error import reraise, exceptionAsUnicode
from ufwi_rpcd.common.process import createProcess, communicateProcess
from ufwi_rpcd.core import mustreapply, del_reapply_stamp
from ufwi_rpcd.core.config.responsible import (HA_FIRST_REPLICATION,
    HA_FULL_SYNCHRONIZATION, HA_INCREMENTAL)
from ufwi_rpcd.core.context import Context
from ufwi_conf.backend.ha import readHaType, saveHaType
from ufwi_conf.backend.unix_service import ConfigServiceComponent
from ufwi_conf.common.ha_base import PRIMARY_ADDR, SECONDARY_ADDR, getHostnameFormatHA
from ufwi_conf.common.ha_cfg import (ACTIVE, AUTO_FAILBACK, HAConf, INACTIVE,
    NOT_CONNECTED, NOT_REGISTERED, UDP_PORT)
from ufwi_conf.common.ha_statuses import PRIMARY, PENDING_PRIMARY, SECONDARY, \
    PENDING_SECONDARY, ENOHA
from ufwi_conf.common.netcfg import deserializeNetCfg
from ufwi_conf.common.site2site_cfg import Site2SiteCfg
from ufwi_conf.common.user_dir import AD, NuauthCfg

from .error import CreateHaFailed, InvalidConf, InvalidCallDone, \
    SecondaryFailedToApply, InitScriptConfigError
from .netcfg import HaNetCfg
from .primary.primary_host import PrimaryHost
from .secondary.secondary_host import SecondaryHost

# Check for active/passive state modifications ever 5 minutes
ACTIVE_CHECK_TIME = 5*60
PASSWORD_LENGTH = 16

def lambda_x(func, *args):
    return lambda x: func(*args)

HA_CF = '/etc/ha.d/ha.cf'
HA_RESOURCES = '/etc/ha.d/haresources'

class HAComponent(ConfigServiceComponent):
    NAME = "ha"
    MASTER_KEY = NAME
    VERSION = "1.1"
    """ Versions:
    - 1.1:
        - add getFullState service
    """
    PIDFILE = '/var/run/heartbeat.pid'
    INIT_SCRIPT = 'heartbeat'
    EXE_CAN_RELOAD = True

    REQUIRES = ('multisite_transport', 'hosts')

    ACLS = {'config' : set(('getConfigSequenceNumber', 'apply',
                'apply_post_update',)),
            'contact': set(('sendMailToAdmin',)),
            'ha': set(('hello', 'bye', 'getState', 'getFullState', 'status',
                'start', 'reload', 'restart', 'stop', 'setConfig', 'callRemote',
                'register','unregister', 'end_registration', 'importOrIgnore',
                'ufwi_rulesetImport')),
            'hostname': set(('getPrimaryHostname',)),
            'localfw': set(('open', 'addFilterRule', 'apply', 'close')),
            'logger': set(('get_log',)),
            'multisite_transport': set(('setSelf', 'addRemote', 'removeRemote',
                'callRemote', 'getPort', 'start', 'stop', 'hostFile',
                'removeFile', 'getFile')),
            'network': set(('getNetconfig', 'setNetconfig')),
            'ntp': set(('setDate', )),
            'nuauth': set(('getNuauthConfig',)),
            'ufwi_ruleset': set(('reapplyLastRuleset',)),
            'nurestore': set(('duplicate', 'import',)),
            'site2site': set(('getConfig', 'setEnabledOnBoot')),
            'update': set(('getKnownUpgradeNums',)),
            '*' : set(('runtimeFiles', 'runtimeFilesModified', 'onHAActive',
                'onHAPassive')),
            }

    ROLES = {
        'conf_read' : set(("getConfig", "callRemote", "getHAMode",
            "getHAActive", "getMissingUpgradeNums", "getState", "getFullState",
            "getLastError", )),
        'conf_write' : set(("@conf_read", "configureHA", "startHA",
             "ufwi_rulesetImport", "ufwi_rulesetExport", "takeover"
        ))
    }

    # hostname: /etc/ha.d/haressources & /etc/ha.d/ha.cf contain hostnames of
    #           primary and secondary
    # network, nuauth & ipsec are haresources
    CONFIG_DEPENDS = frozenset(('hostname', 'network', 'nuauth'))

    _IMPORT_INTERVAL = 1 # second
    HA_STATUS_FILE = None

    def __init__(self):
        ConfigServiceComponent.__init__(self)
        self.config = None
        self.core = None
        self.ha = None
        self.ha_ready = False
        self.cb_configModified = None

        # Hearbeat active / passive status
        self.heartbeat_mon_task = None
        self.is_active = True

        # List of components needing notifications of state modifications
        self.on_active_component = []
        self.on_passive_component = []

        #Slave things
        #Where we store the downloaded next config before we apply it
        self._next_setConfig = None
        #lock before doing a setConfig
        self._setConfig_lock = Lock()
        self.__call_scheduled = False

    def getType(self):
        return self.config.ha_type

    def init(self, core):
        ConfigServiceComponent.init(self, core)
        self.debug("High Availability type: %s" % unicode(self.config.ha_type))

        if self.config.ha_type == PRIMARY:
            self.cb_configModified = self.core.notify.connect('*', 'configModified', self.configModified)

        self.addConfFile(HA_CF, 'root:root', '0644')
        self.addConfFile(HA_RESOURCES, 'root:root', '0644')
        self.addConfFile('/etc/init.d/heartbeat_edw', 'root:root', '0755')
        self.addConfFile('/etc/ha.d/resource.d/conntrackd', 'root:root', '0755')
        self.addConfFile('/etc/ha.d/resource.d/edw', 'root:root', '0755')
        self.addConfFile('/etc/ha.d/resource.d/IPaddr2EW', 'root:root', '0755')
        self.addConfFile('/etc/ha.d/resource.d/iproute', 'root:root', '0755')
        self.addConfFile('/etc/conntrackd/conntrackd.conf', 'root:root', '0644')
        self.addConfFile('/usr/lib/ocf/resource.d/heartbeat/IPaddr2EW', 'root:root', '0755')
        self.addConfFile('/usr/lib/ocf/resource.d/heartbeat/iproute', 'root:root', '0755')
        self.addConfFile('/usr/share/heartbeat/ResourceManager', 'root:root', '0755')

        self.HA_STATUS_FILE = join(core.config.get('CORE', 'vardir'), 'ha_status')
        self.startHeartbeatMonitor()
        return self.createHA()

    @inlineCallbacks
    def saveNotHaResources(self):
        """See documentation in netcfg.HaNetCfg.saveNotHaResources"""
        context = Context.fromComponent(self)
        netcfg = yield self.getNetConfig(context)
        netcfg.saveNotHaResources(self.config.ha_type)

    @inlineCallbacks
    def apply_config(self, responsible, arg, modified_paths):
        yield self.saveNotHaResources()
        # restart heartbeat: become passive, so release all resources
        yield ConfigServiceComponent.apply_config(self, responsible, arg,
            modified_paths)
        responsible.storage['ha_resource_released'] = True

    @inlineCallbacks
    def rollback_config(self, responsible, arg, modified_paths):
        yield self.configure(responsible)
        # Become active taking all resources if ha.apply_config have been
        # previously called.
        # Rollbacks which occur on the secondary must not take ressources !
        if self.config.ha_type == PRIMARY and\
            responsible.storage.get('ha_resource_released', False):
            # currently heartbeart doesn't need to reload conf (but if #995)
            # is implemented it is necessary if watchdog configuration has
            # been modified
            # yield deferToThread(self.startstopManager, 'restart')
            yield self.takeover()

    @inlineCallbacks
    def init_done(self):
        ctx = Context.fromComponent(self)
        components = yield self.core.callService(ctx, 'CORE', 'getComponentList')
        yield self.setAllComponentCallbacks(components)
        self.ha_ready = True
        yield self._reapply_if_needed()

    @inlineCallbacks
    def _reapply_if_needed(self):
        # if stamp file not here, nothing to do
        if not mustreapply():
            returnValue(None)

        self.critical("Post load: A reapplication of the whole configuration is scheduled.")

        del_reapply_stamp()

        remote_ok = True

        if self.config.ha_type == PRIMARY:
            # duplicate tdb and sid (done even if AD not used but it's not a
            # problem)
            yield self.syncConfig(HA_INCREMENTAL, ['nuauth'])

            #remote first
            self.critical(
                "We are primary; calling config.apply_post_update() "
                "on the secondary"
                )
            remote_ok = yield self.ha.remotePostUpdate()
            if not remote_ok:
                self.critical(
                    "config.apply_post_update() didn't go well "
                    "on the secondary."
                    )
        else:
            self.debug(
                "We are not primary; not calling config.apply_post_update() "
                "on the secondary"
                )

        if remote_ok and self.config.ha_type != SECONDARY:
            #SECONDARY must wait for PRIMARY to ask
            #local
            self.critical(
                "We are not secondary. Calling config.apply_post_update() "
                "locally."
                )
            context = Context.fromComponent(self)
            yield self.core.callService(context, 'config', 'apply_post_update')
            if self.config.ha_type == PRIMARY:
                # tdb have been modified by previous apply_post_update, so
                # duplicate tdb again (done even if AD not used but it's not a
                # problem)
                yield self.syncConfig(HA_INCREMENTAL, ['nuauth'])
                # takeover needed because application done first on secondary
                yield self.takeover()
        elif self.config.ha_type == SECONDARY:
            self.critical(
                    "Secondary not calling config.apply_post_update() "
                    "now. We wait for the primary to call it when it is ready"
               )

    @inlineCallbacks
    def setAllComponentCallbacks(self, components):
        ctx = Context.fromComponent(self)
        for component in components:
            services = yield self.core.callService(ctx, 'CORE', 'getServiceList', component)
            if 'onHAActive' in services:
                self.on_active_component.append(component)
            if 'onHAPassive' in services:
                self.on_passive_component.append(component)

    def startHeartbeatMonitor(self):
        self.is_active = self.getActiveState()
        self.restartHeartbeatMonitor()

    def restartHeartbeatMonitor(self):
        if self.heartbeat_mon_task is not None:
            self.heartbeat_mon_task.stop()
        self.heartbeat_mon_task = scheduleRepeat(ACTIVE_CHECK_TIME, self.refreshActiveState)

    def refreshActiveState(self):
        # we are inside a timer, returning the deferred is useless
        self._refreshActiveState()

    @inlineCallbacks
    def _refreshActiveState(self):
        ctx = Context.fromComponent(self)
        previous_state = self.is_active
        self.is_active = self.getActiveState()

        if previous_state != self.is_active:
            if self.is_active:
                self.info(tr('HA switched to active state'))
                cb = 'onHAActive'
                lst = self.on_active_component
            else:
                self.info(tr('HA switched to passive state'))
                cb = 'onHAPassive'
                lst = self.on_passive_component

            # Notify component of the state modification
            for component in lst:
                try:
                    yield self.core.callService(ctx, component, cb)
                except Exception, err:
                    self.writeError(err, "Error while changing state in component %s" % component)

        returnValue(self.is_active)

    def getActiveState(self):
        if self.config.ha_type in ['ENOHA', 'PENDING_PRIMARY', 'PENDING_SECONDARY']:
            return True

        try:
            status_file = open(self.HA_STATUS_FILE, 'r')
            status_content = status_file.readline().strip()
            if status_content == ACTIVE:
                return True
            elif status_content == INACTIVE:
                return False
            else:
                self.debug('HA status contains an unknown status: %s' % status_content)
                return False
        except IOError:
            self.debug('HA status is not readable')
        return False

    #################
    # ConfigServiceComponent

    def read_config(self, responsible, *args, **kwargs):
        if responsible is not None and responsible.caller_component == "ha":
            return

        try:
            serialized = self.core.config_manager.get(self.NAME)
            self.config = HAConf.deserialize(serialized)
        except Exception, err:
            self.debug("config not loaded, generate default configuration")
            self.config = HAConf(ha_type=ENOHA)

        try:
            directory = self.core.config.get('CORE', 'vardir')
            self.config.ha_type = readHaType(directory)
        except Exception, err:
            self.config.ha_type = ENOHA
            self.critical('Invalid HA type')
            self.writeError(err, "Error on reading HA config")

    def save_config(self, message, context=None, set_all_config=False):
        """
        override ConfigServiceComponent save_config
        """
        with self.core.config_manager.begin(self, context) as cm:
            try:
                cm.delete(self.NAME)
            except ConfigError:
                # Means the value does not exist in the first place
                pass

            serialized = self.config.serialize()
            serialized['ha_type'] = '' # ha_type is store in a specific file
            cm.set(self.NAME, serialized)

            if set_all_config:
                #Data wise, this is a NO-OP
                #Purpose is to force the reapplication of many ufwi_conf modules
                all_config = cm.get()
                # We don't need to reset nuauth, and it may
                # cause an unnecessary join
                for item in 'nuauth nuauth_bind'.split():
                    if item in all_config:
                        del all_config[item]
                cm.set(all_config)

            cm.commit(message)

        with self.core.config_manager.begin(self, context) as cm:
            # Mark network configuration as modified in order to force the generation
            # of /etc/network/interfaces file when status of HA is modified. For
            # example if an interface has been configured with service and primary
            # ips /etc/network/interfaces is different in PENDING_PRIMARY state and
            # in PRIMARY state.

            network_key = 'network'
            net_conf = cm.get(network_key)
            try:
                cm.delete(network_key)
            except ConfigError:
                pass
            cm.set(network_key, net_conf)

            # Mark ntp configuration as modified in order to force the generation
            # of /etc/ntp.conf file when status of HA is modified.

            ntp_key = 'ntp'
            try:
                ntp_conf = cm.get(ntp_key)
            except ConfigError:
                ntp_conf = None
            else:
                try:
                    cm.delete(ntp_key)
                except ConfigError:
                    pass
                cm.set(ntp_key, ntp_conf)
            if ntp_conf is None:
                self.debug("While flagging ntp configuration as modified: no ntp config was registred.")
                message = 'HA : flag network configuration as modified.'
            else:
                message = 'HA : flag network and ntp configuration as modified.'
            cm.commit(message)

        directory = self.core.config.get('CORE', 'vardir')
        result = saveHaType(directory, self.config.ha_type)
        if not result:
            self.error('Saving HA type failed (%s)' % directory)

    def should_run(self, responsible):
        return self.config.ha_type in [PRIMARY, SECONDARY]

    @inlineCallbacks
    def genConfigFiles(self, responsible):
        if self.config.ha_type == ENOHA:
            responsible.feedback(
                tr("High availability is currently not configured; skipping.")
                )
            # hostname modified but ha not activated
            for previous_file in (HA_CF, HA_RESOURCES):
                if exists(previous_file):
                    unlink(previous_file)
            return

        template_variables = yield self.templatesConfiguration()
        self.generate_configfile(template_variables)

        # create symbolic links for heartbeat_edw: this script overwrite
        # /var/lib/ufwi_rpcd/ha_status (if exists) with "INACTIVE"
        cmd = "update-rc.d heartbeat_edw start 19 2 3 4 5 ."
        process = createProcess(self, cmd.split(), stdout=PIPE, stderr=STDOUT, locale=False)
        results = communicateProcess(self, process, DEFAULT_TIMEOUT) # status, stdout, stderr
        if results[0] != 0:
            err = "Command '%s' failed: '%s'" % (cmd, results[1])
            raise InitScriptConfigError(err)

        yield self.createHA()

    @inlineCallbacks
    def templatesConfiguration(self):
        context = Context.fromComponent(self)
        netcfg = yield self.getNetConfig(context)
        hostname = yield self.core.callService(context, 'hostname', 'getPrimaryHostname')

        # ipsec is an ha resource
        # Enable ipsec on boot if and only if no HA and some VPN is used.
        try:
            raw_site2site_cfg = yield self.core.callService(context, 'site2site', 'getConfig')
            site2site_cfg = Site2SiteCfg.deserialize(raw_site2site_cfg)
            vpn_used = site2site_cfg.isVpnUsed()
        except Exception, err:
            vpn_used = False
            err_title = 'Error when reading VPN site to site configuration'
            self.writeError(err, title=err_title)

        # When configuration change from HA enabled to ENOHA, we must
        # re-enable ipsec on boot
        if vpn_used and self.config.ha_type == ENOHA:
            try:
                yield self.core.callService(context, 'site2site', 'setEnabledOnBoot', True)
            except Exception, err:
                err_title = 'Error when enabling VPN site to site on boot'
                self.writeError(err, title=err_title)

        # winbind is an ha ressource
        try:
            raw_nuauth_cfg = yield self.core.callService(context, 'nuauth', 'getNuauthConfig')
            nuauth_cfg = NuauthCfg.deserialize(raw_nuauth_cfg)
            ad_is_used = nuauth_cfg.org.protocol == AD
        except Exception, err:
            ad_is_used = False
            self.writeError(err, title='Error reading user directory configuration')

        if self.config.ha_type == PRIMARY:
            ip_of_dedicated_local_link = PRIMARY_ADDR
            ip_of_dedicated_remote_link = SECONDARY_ADDR
        else:
            ip_of_dedicated_local_link = SECONDARY_ADDR
            ip_of_dedicated_remote_link = PRIMARY_ADDR

        returnValue({
            'DEDICATED_INTERFACE_NAME': self.config.interface_name,
            'HEARTBEAT_FAILBACK': AUTO_FAILBACK,
            'HEARTBEAT_UDP_PORT': UDP_PORT,
            'IP_OF_DEDICATED_LOCAL_LINK': ip_of_dedicated_local_link,
            'IP_OF_DEDICATED_REMOTE_LINK': ip_of_dedicated_remote_link,

            'PRIMARY_HOSTNAME': getHostnameFormatHA(PRIMARY) % hostname,
            'SECONDARY_HOSTNAME': getHostnameFormatHA(SECONDARY) % hostname,

            'ad_is_used': ad_is_used,

            'ha_ip_definitions': netcfg.ipResources(),
            'ha_routes_definitions': netcfg.routeResources(),
        })

    @inlineCallbacks
    def createHA(self):
        """
        instantiate primary or secondary
        type is guessed reading ha_type.xml file

        return a deferred
        """
        if self.config.ha_type not in [PRIMARY, PENDING_PRIMARY, SECONDARY, PENDING_SECONDARY]:
            # HA not configured
            return

        # TODO PRIMARY -> SECONDARY should not be possible
        if self.config.ha_type == PENDING_PRIMARY or self.config.ha_type == PRIMARY:
            if (isinstance(self.ha, PrimaryHost)
               and self.config.interface_id == self.ha.config.interface_id):
                return
            # else configuration modified, modifications are taken in account

        if self.config.ha_type == PENDING_SECONDARY or self.config.ha_type == SECONDARY:
            if (isinstance(self.ha, SecondaryHost)
               and self.config.interface_id == self.ha.config.interface_id):
                return
            # else configuration modified, modifications are taken in account

        if self.ha is not None:
            yield self.ha.stop()

        if self.config.ha_type == PENDING_PRIMARY or self.config.ha_type == PRIMARY:
            self.ha = PrimaryHost(self, self.core, self.config)
        elif self.config.ha_type == PENDING_SECONDARY or self.config.ha_type == SECONDARY:
            self.ha = SecondaryHost(self, self.core, self.config)

        self.info('Starting HA as %s' % self.config.ha_type)

        yield self.ha.loadConfig()

    def checkHAType(self, ha_type):
        """
        must be used as assert
        """
        if self.config is None:
            raise InvalidCallDone('Invalid call done : not yet configured')

        if isinstance(ha_type, list):
            if self.config.ha_type not in ha_type:
                raise InvalidCallDone('Invalid call done : current state=%s expected=%s' % (self.config.ha_type, ','.join(ha_type)))
        else:
            if self.config.ha_type != ha_type:
                raise InvalidCallDone('Invalid call done : current state=%s expected=%s' % (self.config.ha_type, ha_type))

    def setState(self, state):
        """
        return a defer
        """
        self.config.ha_type = state
        self.config.password = ''
        self.save_config("HA: Switching to state: %s" % state)

    def takeover(self):
        self.info('Try to become active node: launch takeover')
        cmd = '/usr/share/heartbeat/hb_takeover all'.split()
        return deferToThread(runCommand, self, cmd, timeout=60, env={})

    #################
    # Common services to primary and secondary
    def service_getHAMode(self, ctx):
        return self.config.ha_type

    @inlineCallbacks
    def service_getHAActive(self, ctx):
        yield self._refreshActiveState()
        returnValue(self.is_active)

    def service_configureHA(self, ctx, serialized, message):
        new_cfg = HAConf.deserialize(serialized)

        validity = new_cfg.isValidWithMsg()

        previous_status = self.config.ha_type

        if validity is None:
            self.config = new_cfg
        else:
            raise InvalidConf(*validity)

        must_set_all_config = (
            previous_status == SECONDARY and self.config.ha_type == PENDING_PRIMARY
            )
        self.save_config(message, ctx, set_all_config=must_set_all_config)

    def startFailed(self, err):
        def returnError(unused, new_err):
            # keep backtrace
            reraise(new_err)

        ctx = Context.fromComponent(self)
        if self.config.ha_type == PRIMARY:
            self.core.notify.disconnect('*', 'configModified', self.cb_configModified)
            self.setState(PENDING_PRIMARY)
            defer = self.core.callService(ctx, 'config', 'apply')
        elif self.config.ha_type == SECONDARY:
            self.setState(PENDING_SECONDARY)
            defer = self.core.callService(ctx, 'config', 'apply')
        else:
            defer = succeed(None)

        # always return original error
        new_err = CreateHaFailed(exceptionAsUnicode(err))
        defer.addCallback(returnError, new_err)
        return defer

    def service_getConfig(self, ctx):
        return self.config.serialize()

    def service_getState(self, ctx):
        """
        DEPRECATED, use getFullState
        return list containing:
            - connectivity (NOT_REGISTERED, CONNECTED / NOT_CONNECTED)
            - date of last response of other node
            - last error
        """
        if self.config.ha_type != SECONDARY and self.config.ha_type != PRIMARY:
            return [NOT_CONNECTED, 0, '']
        component_ctx = Context.fromComponent(self)
        return self.ha.getState(component_ctx)

    @inlineCallbacks
    def service_getFullState(self, ctx):
        """
        return dict containing:
            - 'node_state': active / passive / not registered
            - 'link_state': connected / not connected
            - 'seen_other': date of last response of other node
            - 'last_error': last error on this node
        """
        if self.config.ha_type != SECONDARY and self.config.ha_type != PRIMARY:
            returnValue({
                'node_state': NOT_REGISTERED,
                'link_state': NOT_CONNECTED,
                'seen_other': 0,
                'last_error': '',
            })

        component_ctx = Context.fromComponent(self)
        data = self.ha.getState(component_ctx)
        result = {
            'link_state': data[0],
            'seen_other': data[1],
            'last_error': data[2],
        }

        # update self.is_active
        yield self._refreshActiveState()

        if self.is_active:
            result['node_state'] = ACTIVE
        else:
            result['node_state'] = INACTIVE

        returnValue(result)

    @inlineCallbacks
    def service_callRemote(self, *args):
        """
        wrapper for multisite_transport.callRemote(...)
        """
        # PENDING_PRIMARY needed
        self.checkHAType([PENDING_PRIMARY, PRIMARY, SECONDARY])

        component, service = args[1], args[2]
        if self.config.ha_type == PENDING_PRIMARY:

            _VALID_CALLS = (
                (self.NAME, 'setConfig'),
                )

            if (component, service) in _VALID_CALLS:
                self.info('Doing first configuration synchronisation')
            else:
                msg = "Invalid call done (%s.%s). "+\
                "While my current state is %s expected=PRIMARY"
                raise InvalidCallDone(msg % (component, service, self.config.ha_type))

        self.debug("other node call %s.%s" % (component, service))
        ret = yield self.ha.service_callRemote(*args)
        self.debug("Call %s.%s by other node done" % (component, service))
        returnValue(ret)

    @inlineCallbacks
    def service_syncTime(self, context):
        if self.config.ha_type != PRIMARY:
            returnValue(None)

        newtime = unicode(datetime.today())
        yield self.service_callRemote(
            Context.fromComponent(self),
            'ntp',
            'setDate',
            newtime
            )

    def service_unregister(self, ctx):
        return self.ha.unregister()

    def service_getLastError(self, ctx):
        if self.ha is None:
            return u''
        return self.ha.getLastError()

    def service_bye(self, *args):
        # We can receive a bye in any state while reconfiguring
        #self.checkHAType(PRIMARY)
        return self.ha.service_bye(*args)

    #################
    # Primary only services
    @inlineCallbacks
    def service_startHA(self, ctx):
        self.checkHAType([PENDING_PRIMARY, PRIMARY])
        try:
            yield self.createHA()
            conf = self._getConf()
            self.generateAuthkeys(conf['password'])

            yield self.ha.register(conf)
            # --> On secondary read_config of all modules can read
            # /var/lib/ufwi_rpcd/ha_type, config is applied
        except Exception, err:
            self.writeError(err, 'HA start failed')
            yield self.startFailed(err)
        else:
            if not self.cb_configModified:
                self.cb_configModified = self.core.notify.connect('*',
                    'configModified', self.configModified)

    @inlineCallbacks
    def service_end_registration(self, ctx, *args):
        # XXX context parameter reusable here ?
        self.checkHAType([PENDING_PRIMARY, PRIMARY])
        context = Context.fromComponent(self)
        self.setState(PRIMARY)

        # call to apply which doesn't trigger a configuration synchronisation
        errors = yield self.core.callService(context, 'config', 'apply')
        if errors:
            raise CreateHaFailed(tr("Application error encountered on primary node"))

        #Force takeover: 'hb_takeover all'
        #
        #Purpose (info from Pierre-Louis Bonicoli):
        #The command "cl_status rscstatus" is not yielding
        #expected values
        #
        #Expected:
        # * "all" on active,
        # * "none" on passive
        #Read values:
        # * "local" on both
        yield self.takeover()

        # explicit synchronisation
        yield self.syncConfig(HA_FIRST_REPLICATION)

    @inlineCallbacks
    def service_hello(self, *args):
        self.checkHAType([PENDING_PRIMARY, PRIMARY])
        if self.config.ha_type == PRIMARY:
            need_sync = yield self.ha.service_hello(*args)
            # TODO hello should return difference between version instead of a boolean
            # then HA_INCREMENTAL could be used
            yield self.triggerSyncConfig(need_sync)

    @inlineCallbacks
    def service_getMissingUpgradeNums(self, ctx, *args):
        context = Context.fromComponent(self)
        try:
            primary_upgrades = yield self.core.callService(context, 'update', 'getKnownUpgradeNums')
            secondary_upgrades = yield self.ha.service_callRemote(context, 'update', 'getKnownUpgradeNums')
            primary_upgrades = set(primary_upgrades)
            secondary_upgrades = set(secondary_upgrades)
            returnValue(list(primary_upgrades - secondary_upgrades))
        except Exception, err:
            self.writeError(err, "Error on getting missing upgrades")
            raise

    @inlineCallbacks
    def service_takeover(self, context):
        yield self.takeover()

    def _getConf(self):
        """
        return configuration for self.ha.register
        """
        # hard label of ha interface on secondary will be compared with hard
        # label of ha interface on secondary
        # python3: password = ''.join(('%02x' % ord(x)) for x in rand_bytes(PASSWORD_LENGTH))
        password = rand_bytes(PASSWORD_LENGTH).encode('hex')

        return {
            'interface': self.config.interface_id,
            'date': unicode(datetime.today()),
            'password': password,
        }

    def generateAuthkeys(self, password):
        """generate /etc/ha.d/authkeys file"""
        template_variables = {'HEARTBEAT_PASSWORD': password, }
        self.renderTemplate('/etc/ha.d/authkeys', template_variables, '0600', 'root:root')

    @inlineCallbacks
    def triggerSyncConfig(self, need_sync):
        self.info("Hello received from other, synchronized: %s" % (not need_sync))
        if need_sync:
            # passive replication: secondary ask replication
            yield self.syncConfig(HA_FULL_SYNCHRONIZATION)

    def configModified(self, context):
        """
        component : name of component which emit signal

        pro-active replication: primary sends its recent modification to secondary

        return a deferred
        """
        if not self.ha_ready:
            self.info("'configModified' signal can not be handled, component is not ready.")
            return

        if hasattr(context, 'components'):
            components = context.components
        else:
            components = [context.sender]

        if hasattr(context, 'config_keys'):
            config_keys = context.config_keys
        else:
            config_keys = ''

        msg = "Module '%s' modified configuration: replicate new configuration (%s)"
        self.info(msg % (context.sender, components))

        # don't return the deferred, primary application must not wait
        # secondary application
        self.syncConfig(HA_INCREMENTAL, components, config_keys)

    @inlineCallbacks
    def syncConfig(self, action, components=None, config_keys=''):
        """
        Replicate configuration of primary on secondary

        action in HA_INCREMENTAL, HA_FIRST_REPLICATION, HA_FULL_SYNCHRONIZATION

         Algorithm:
          get list of modified components
          create encoded tar file with configuration
          if there is something to export:
            host encoded tar file on active server
            from passive, fetch, decode, untar file
            foreach component which has exported something:
                try:
                    warn component that runtime files have been modified
                except:
                    log error
          remove some components from the list of modified components
        """

        if action not in (HA_INCREMENTAL, HA_FIRST_REPLICATION,
            HA_FULL_SYNCHRONIZATION):
            raise ValueError('Unknow action parameter : %s' % action)


        if action == HA_INCREMENTAL and 'config' not in components:
            # Only config component support incremental replication, for example
            # with ufwi_ruleset, whole configuration is replicated

            # TODO config_keys should be None if action != HA_INCREMENTAL, if not raise ValueError
            self.debug("Not able to do incremental replication with component which is not 'config'")

        if action == HA_INCREMENTAL and components == ['config'] and not config_keys:
            raise ValueError('incremental replication need components parameter')

        self.checkHAType([PENDING_PRIMARY, PRIMARY])
        ctx = Context.fromComponent(self)
        if config_keys:
            all_components = components + config_keys
        else:
            all_components = components
        result = yield self.core.callService(ctx, 'nurestore', 'duplicate', all_components)
        if not isinstance(result, tuple):
            self.debug('no file returned by nurestore.duplicate(...)')
            returnValue(None)
        else:
            data, components_exported = result

            components_modified = yield self.copyConfiguration(ctx, data,
                components_exported, config_keys, action)
            self.debug('exported: %s' % unicode(components_exported))
            # TODO components_modified is always None !
            self.debug('modified: %s' % unicode(components_modified))

    @inlineCallbacks
    def copyConfiguration(self, ctx, data, components, config_keys, action):
        """
        - host configuration file and fetch file remotely
        - runtime files of component listed in components have been modified :
            each component must be warned about that

        We are on primary
        """

        assert ctx.component

        if components is None:
            components = []
        data_file = yield self.core.callService(
            ctx, 'multisite_transport', 'hostFile', data
            )
        try:
            components_modified = yield self.service_callRemote(ctx, 'ha',
                'setConfig', data_file, components, config_keys, action)
        except Exception, err:
            self.ha.saveError(err)
            yield self.ha.sendLastSecondaryError()
            raise
        returnValue(components_modified)

    #################
    # Secondary only services

    @inlineCallbacks
    def filesModified(self, components, config_keys, action):
        """
        call service runtimeFilesModified on each components

        We are on secondary
        """
        # at first : config component
        first = 'config'
        if first in components:
            components.remove(first)
            components.insert(0, first)
        elif action in (HA_FIRST_REPLICATION, HA_FULL_SYNCHRONIZATION):
            components.insert(0, first)

        # XXX remove when #855 fixed
        if 'acl' in components and 'CORE' in components:
            acl_index = components.index('acl')
            CORE_index = components.index('CORE')
            if acl_index < CORE_index:
                components[CORE_index], components[acl_index] =\
                components[acl_index], components[CORE_index]

        ctx = Context.fromComponent(self)

        self.debug("Components are informed that their external configuration "
            "has been modified")
        successful = []
        for component in components:
            try:
                if component == 'config':
                    # only config take parameters
                    if config_keys:
                        options = {'action': action, 'paths_file': config_keys}
                    else:
                        options = {'action': HA_FULL_SYNCHRONIZATION}
                    errors = yield self.core.callService(ctx, 'config',
                        'runtimeFilesModified', options)
                    if errors:
                        raise SecondaryFailedToApply(errors)
                else:
                    try:
                        services = self.core.getServiceList(ctx, component)
                    except AclError:
                        continue

                    if 'runtimeFilesModified' in services:
                        self.debug("'%s.%s()' found" % (unicode(component),
                            u'runtimeFilesModified'))
                        yield self.core.callService(ctx, component,
                            'runtimeFilesModified')
            except SecondaryFailedToApply, err:
                self.writeError(err,
                    "Error on calling %s.runtimeFilesModified()" % component)
                raise
            except Exception, err:
                self.writeError(err,
                    "Error on calling %s.runtimeFilesModified()" % component)
                if action == HA_FIRST_REPLICATION:
                    raise
            else:
                successful.append(component)
        self.debug("Components have been informed that their external"
            " configuration has been modified")
        returnValue(successful)

    @inlineCallbacks
    def service_register(self, ctx, configuration):
        component_ctx = Context.fromComponent(self)
        try:
            self.checkHAType([PENDING_SECONDARY, SECONDARY])
            yield self.core.callService(
                component_ctx,
                'ntp',
                'setDate',
                configuration['date']
                )

            # if no password specified use old fixed password,
            # should not happen, part of #1055
            if not configuration.has_key('password'):
                self.debug(
                    'HA registration using old authentication scheme, '
                    'primary need to be updated'
                    )
            password = configuration.get('password','TODO XXX BUG Change me')
            self.generateAuthkeys(password)

            self.restartHeartbeatMonitor()
            yield self.ha.register(configuration)
        except Exception, err:
            self.writeError(err, 'HA register failed')
            yield self.startFailed(err)

    def __addNextConfig(self, encoded_file, components, config_keys):
        self._next_setConfig = encoded_file, components, config_keys

    @inlineCallbacks
    def service_setConfig(self, ctx, config_url, components, config_keys, action):
        """
        Through this service, the secondary gets to know that there is a new config in town.

        1) Download the config (multisite_transport.getFile)
        2) store the download in self._next_setConfig
        3) call the local service importOrIgnore
        """
        self.checkHAType(SECONDARY)

        # Download the config
        encoded_file = yield self.core.callService(ctx, 'multisite_transport', 'getFile', PRIMARY_ADDR, config_url)
        yield self.__addNextConfig(encoded_file, components, config_keys)
        yield self.service_importOrIgnore(ctx, action)

    def __popNextConfig(self):
        result = self._next_setConfig
        self._next_setConfig = None
        return result

    def __scheduleImportOrIgnore(self, action):
        if self.__call_scheduled:
            return "Already scheduled"

        self.debug("schedule call to 'importOrIgnore'")
        context = Context.fromComponent(self)

        scheduleOnce(
            self.__class__._IMPORT_INTERVAL,
            self.core.callService,
            context,
            self.NAME,
            'importOrIgnore',
            action,
            )

        self.__call_scheduled = True
        return "Scheduled import"

    def __simpleLockRelease(self, arg=None):
        """arg used by twisted"""
        self._setConfig_lock.release()
        return arg

    @inlineCallbacks
    def service_importOrIgnore(self, context, action):
        """
        A private service that only this component can call

        It is a way to implement recursivity in twisted.
        Try to import, unless an import is already running, in which case we postpone.
        Only the most recent data is kept.

        Algo:

         while not acquire_lock():
              sleep(1)

         config = pop(next_config)
         if config == NULL:
              unlock()
              return

         try:
              import(config)
         finally:
              unlock()

        in case of an error, it will be propagated, but the lock is released notwihstanding
        """

        #Attempt to take the lock, NOT blocking
        if not self._setConfig_lock.acquire(False):
            returnValue(self.__scheduleImportOrIgnore(action))

        self.__call_scheduled = False

        item = self.__popNextConfig()
        if item is None:
            self.debug('importOrIgnore : ignore')
            #release the lock
            self.__simpleLockRelease()
            returnValue("Nothing to import")

        yield self.core.notify.emit(self.NAME, 'ImportStart')
        self.debug('importOrIgnore : import')
        to_import, components, config_keys = item
        yield self.importConfigFile(to_import)
        try:
            ret = yield self.filesModified(components, config_keys, action)
        except Exception, err:
            self.writeError(err, "importOrIgnore failure")
            raise err
        else:
            returnValue(ret)
        finally:
            # always release the lock
            yield self.__simpleLockRelease()
            yield self.core.notify.emit(self.NAME, 'ImportEnd')

    def importConfigFile(self, encoded_file):
        context = Context.fromComponent(self)
        return self.core.callService(context, 'nurestore', 'import', encoded_file)

    @inlineCallbacks
    def getNetConfig(self, context):
        """
        return current netcfg config with ha helpfull method
        """
        raw_netcfg = yield self.core.callService(context, 'network', 'getNetconfig')
        netcfg = deserializeNetCfg(raw_netcfg)
        netcfg = HaNetCfg(netcfg) # adapt to ha
        returnValue(netcfg)

    def service_ufwi_rulesetImport(self, context, url):
        """
        Download and write the files from the primary and apply the (new)
        production ruleset.

        Should only be called on the secondary.
        """
        self.checkHAType(SECONDARY)

        # Use HAComponent context to get the permissions
        context = Context.fromComponent(self)

        defer = self.core.callService(context, 'multisite_transport', 'getFile', PRIMARY_ADDR, url)
        defer.addCallback(lambda tar_content: self.core.callService(context, 'nurestore', 'import', tar_content))
        defer.addCallback(lambda unused: self.core.callService(context, 'ufwi_ruleset', 'reapplyLastRuleset'))
        return defer

    def service_ufwi_rulesetExport(self, context):
        """
        Export the new applied ruleset to the secondary, and reapply the
        ruleset and the secondary.
        """
        if self.config.ha_type != PRIMARY:
            # Only synchronize ufwi_ruleset on the primary
            return

        # Use HAComponent context to get the permissions
        context = Context.fromComponent(self)

        defer = self.core.callService(context, 'nurestore', 'duplicate', ("ufwi_ruleset",))
        defer.addCallback(self._haHostFile, context)
        defer.addCallback(lambda url: self.service_callRemote(context, 'ha', 'ufwi_rulesetImport', url))
        # FIXME: Use multisite_transport.removeFile()?
        return defer

    def _haHostFile(self, result, context):
        """
        tar_content, components = result
        """
        return self.core.callService(context, 'multisite_transport', 'hostFile', result[0])

