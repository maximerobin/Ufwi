"""
Copyright (C) 2009-2011 EdenWall Technologies
Written by Feth AREZKI <farezki AT edenwall.com>
           Victor STINNER <vstinner AT edenwall.com>
           Pierre-Louis BONICOLI <bonicoli AT edenwall.com>

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

from os.path import join
from os.path import exists
from os import unlink

from twisted.internet.defer import inlineCallbacks
from twisted.internet.defer import returnValue
from twisted.internet.threads import deferToThread

from ufwi_rpcd.backend.component import Component
from ufwi_rpcd.backend.exceptions import ConfigError
from ufwi_rpcd.common import EDENWALL
from ufwi_rpcd.core.context import Context
from ufwi_rpcd.core import mustreapply, del_reapply_stamp

from .manager import ConfigurationManager
from .states import ApplicableState, DraftState, IdleState
from .responsible import (
    Responsible, LOADING_IMPORTED_CONF, CONFIG_MODIFICATION,
    RESTORING_CONFIGURATION, USER_APPLY, INITIAL_APPLY, HA_FULL_SYNCHRONIZATION,
    RESET_CONFIG, UPDATE_WITH_FULL_RELOAD, USER_FORCED_REAPPLICATION)
from .proxy import Proxy

DEFAULT_DIRECTORY = 'configuration'
DEFAULT_FILENAME = 'configuration.xml'

class ConfigComponent(Component):
    API_VERSION = 2
    NAME = 'config'
    VERSION = '1.0'
    REQUIRES = ('lock', 'versionning')
    ROLES = {
        'nucentral_admin': frozenset((
            "get",
            "getKeys",
            "getConfigSequenceNumber",
            "getConfigDiffSequenceNumber",
            "set",
            "delete",
            "reset",
            "listValues",
            "importXML",
            "apply",
            "reApplyAll",
            "applyStart",
            "forceApplyStart",
            "applyLog",
            "clear",
            "isModified",
            "state"
        )),
        'conf_read': frozenset( ( 'state',)),
        'ruleset_read': frozenset( ( 'state',)),
        'log_read': frozenset( ( 'state',)),
        'pki_read': frozenset( ( 'state',)),
        'backup_read': frozenset( ( 'state',)),
        'dpi_read': frozenset( ( 'state',)),
#        'graph_read': frozenset( ( 'state',)),
    }
    if not EDENWALL:
        ROLES['config_get'] = frozenset((
            "get",
            "getKeys",
            "getConfigSequenceNumber",
            "getConfigDiffSequenceNumber",
            "listValues",
            "isModified",
            "state",
        ))
    ACLS = {
        'config': frozenset(('apply_post_update',)),
        'ufwi_conf': frozenset(('takeWriteRole',)),
        'tools': frozenset(('getDiagnosticFile',)),
        'ha': frozenset(('getConfig',)), #in order to see ha component
    }

    # Subscriptions ordered (take in account all relations between components -
    # not only relations defined by REQUIRES)
    def init(self, core):
        self.core = core
        core.notify.config = self
        self.filename = join(DEFAULT_DIRECTORY, DEFAULT_FILENAME)
        self.lock = None

        # FIXME: don't call core._getComponent(). versionning component may
        # FIXME: be converted to a classic class and instanciated here.
        versionning = core._getComponent("versionning")
        self.core.config_manager = self
        vardir = core.config.get('CORE', 'vardir')
        self._restore_stamp = join(vardir, "restore_stamp")
        self.config_manager = ConfigurationManager(self, vardir)
        return self.config_manager.initializeConfig(versionning, self.filename)

    @inlineCallbacks
    def init_done(self):
        yield self._reapply_if_needed()

    @inlineCallbacks
    def _reapply_if_needed(self):
        if not mustreapply():
            #nothing to do
            returnValue(None)

        context = Context.fromComponent(self)
        if EDENWALL and self.core.hasComponent(context, 'ha'):
            #ha component will do the job
            self.critical(
                    "Reapplication of configuration is scheduled. "
                    "HA component will handle it."
                )
            returnValue(None)

        self.critical(
                "Reapplication of configuration started "
                "(handled by config component)."
            )

        yield self.core.callService(context, 'config', 'apply_post_update')

    def begin(
            self,
            component=None,
            user_context=None,
            action=CONFIG_MODIFICATION
            ):
        if component:
            caller_component = component.name
        else:
            caller_component = None
        responsible = Responsible(
            caller_component=caller_component,
            user_context=user_context,
            action=action,
            )
        def rollcallback(*args, **kw):
            self.rollback(*args, **kw)
        self.lock = self.core.lock_manager.acquireVolatile(self.name, rollcallback)
        self.proxy = Proxy(self.config_manager, responsible, ('commit', 'revert', 'rollback'), ('apply', 'reset'), rollcallback)
        return self.proxy

    def rollback(self, *args, **kw):
        trigger = kw.get('trigger')
        if trigger != 'commit' and issubclass(self.config_manager.state, DraftState):
            self.config_manager.rollback()
        self.release()

    def release(self):
        def pass_fn(*args, **kwargs):
            pass

        if self.lock:
            self.lock.callback_fn = pass_fn
            self.core.lock_manager.releaseVolatile(self.name, self.lock)
        self.lock = None

    #Proxies: TODO: factorize
    def apply(self, responsible=None):
        if not issubclass(self.config_manager.state, ApplicableState):
            if issubclass(self.config_manager.state, DraftState):
                #TODO: remove warning
                self.warning("Apply does not commit() implicitely anymore! (this warning will be removed)")
            self.debug("Apply called while there was nothing to be applied")
            return
        return self.config_manager.apply(responsible=responsible)

    def get(self, *args, **kw):
        version = kw.get('which_configuration')
        if version is None:
            fake_state = None
        elif version == 'applied':
            fake_state = IdleState
        elif version == 'saved':
            fake_state = ApplicableState
        else:
            raise ConfigError(
                "Valid values for 'which_configuration' are None, 'applied' and 'saved'"
                )
        if 'which_configuration' in kw:
            kw.pop('which_configuration')
        kw['fake_state'] = fake_state
        return self.config_manager.get(*args, **kw)

    def isDiff(self, which_conf1, which_conf2, *args):
        """
        return True if content under *args path is different in the 2
            configurations, else return False
        """
        try:
            conf1 = self.get(which_configuration=which_conf1, *args)
        except Exception:
            conf1 = {}
        try:
            conf2 = self.get(which_configuration=which_conf2, *args)
        except Exception:
            conf2 = {}
        return conf1 != conf2

    def getKeys(self, *args, **kw):
        return self.config_manager.getKeys(*args, **kw)

    def getValue(self, *args, **kw):
        return self.config_manager.getValue(*args, **kw)

    def items(self, *args, **kw):
        return self.config_manager.items(*args, **kw)

    def subscribe(self, callback, component_name, depends_on, event, *path):
        self.config_manager.subscribe(callback, component_name, depends_on, event, *path)

    #service for debug
    def service_debugRunningConfiguration(self, context):
        return self.config_manager._running_configuration.printMe()

    def service_clear(self, context):
        return self.config_manager.clear()

    @inlineCallbacks
    def service_apply(self, context, responsible=None):
        """
        return a list of encountered errors.
        """
        if responsible is None:
            responsible = Responsible.fromContext(
                context,
                caller_component=self.name,
                action=USER_APPLY
                )

        if self._is_after_restore:
            self._set_restore_stamp(False)

        result = yield self.config_manager.apply(responsible=responsible)
        if result is None:
            result = []
        returnValue(result)

    def __noop(self):
        pass

    def service_forceApplyStart(self, context):
        return self.service_applyStart(context, force=True)

    def service_applyStart(self, context, force=False):
        restore_string = self._after_restore_string()
        if (not force) and restore_string == "restore":
            self.info(
                "Not applying, because the EdenWall just got a brand new "
                "configuration that would trigger a full reload and 'force' "
                "arg is False"
                )
            return "trigger full restoration? then use force=True"

        if restore_string == "restore":
            action = RESTORING_CONFIGURATION
        else:
            action = USER_APPLY

        #A deferToThread has the magical effect of leaving
        #the main loop as soon as reached, so we hand back an unfinished deferred.
        defer = deferToThread(self.__noop)
        defer.addCallback(
            self.service_apply,
            responsible=Responsible.fromContext(context,
                caller_component=self.name,
                action=action,
                )
        )

        return restore_string

    def service_applyLog(self, context, from_seq_nb):
        return self.config_manager.application_journal.getJournal(from_seq_nb)

    def service_reset(self, context):
        responsible = Responsible(caller_component=self.name, action=RESET_CONFIG)
        return self.config_manager.reset(responsible)

    def service_get(self, context, *args):
        return self.config_manager.get(*args)

    def service_set(self, context, *args):
        with self.begin(self, context) as config:
            config.set(*args)
            return config.commit(u"Configuration changed by %s" % unicode(context))

    def service_delete(self, context, *args):
        with self.begin(self, context) as config:
            config.delete(*args)
            return config.commit(u"Configuration changed by %s" % unicode(context))

    def service_getKeys(self, context, *args):
        return tuple(self.config_manager.getKeys(*args))

    def service_items(self, context, *args):
        return self.config_manager.items(*args)

    def service_listValues(self, context, *args):
        return self.config_manager.listValues(*args)

    def service_importXML(self, context):
        return self.config_manager.importXML()

    def service_getConfigSequenceNumber(self, context):
        return self.config_manager.getRunningConfigSequenceNumber()

    def service_getConfigDiffSequenceNumber(self, context):
        return self.config_manager.getConfigDiffSequenceNumber()

    def service_dumpRunningConfiguration(self, context):
        return unicode(self.config_manager._running_configuration)

    def service_isModified(self, context):
        return self.config_manager.isModified()

    def service_state(self, context):
        return self.config_manager.state.NAME

    def service_dumpXML(self, context):
        seq_num = self.config_manager.running_sequence_number
        output = self.config_manager._running_configuration.save(None, seq_num)
        return output.getvalue()

    def service_runtimeFiles(self, context):
        conf = join(
            self.config_manager.filenames.repository.checkout_directory,
            DEFAULT_FILENAME
            )
        deleted = tuple(
            join(
                self.config_manager.filenames.repository.checkout_directory,
                filename
            )
            for filename in self.config_manager.filenames.possible_filenames
            if not filename.startswith("last_working")
            )

        return  {
            'added' : ((conf, 'text'),),
            'deleted': deleted,
            }

    def service_runtimeFilesModified(self, context, options):
        return self.reapply(context, options)

    def service_apply_post_update(self, context):
        del_reapply_stamp()
        options = { 'action': UPDATE_WITH_FULL_RELOAD, }
        return self.reapply(context, options)

    def service_reApplyAll(self, context):
        """
        Applies again all the appliance config.
        Puts saved config on hold and restores it afterwards. Takes time
        """
        del_reapply_stamp()
        options = { 'action': USER_FORCED_REAPPLICATION, }
        return self.reapply(context, options)

    @inlineCallbacks
    def reapply(self, context, options):
        action = options.get('action', None)
        if action is None:
            action = HA_FULL_SYNCHRONIZATION
            self.critical("reapply: action not set, defaulting to action %s" % action)
        self.debug('reapply - %s' % action)
        responsible = Responsible.fromContext(context, action=action)
        yield self.config_manager.reset(responsible)

        if not responsible.implies_full_reload():
            paths_file = options.get('paths_file')
        else:
            paths_file = None
        self.debug("reapply - modified paths are: %s" % paths_file)
        # after remoteLoad: state is applicableState
        # read & apply & rollback callbacks will be computed taking in account paths_file
        yield self.config_manager.remoteLoad(responsible, paths_file)
        errors = yield self.config_manager.apply(responsible=responsible, rotate=False)
        returnValue(errors)

    @inlineCallbacks
    def service_loadImportedConf(self, context, user_context=None, caller_component=None):
        """
        Called by a human being through nurestore
        """
        responsible = Responsible.fromContext(context, action=LOADING_IMPORTED_CONF)
        yield self.config_manager.reset(responsible)
        yield self.config_manager.remoteLoad(responsible, None)
        self._set_restore_stamp(True)
        returnValue('ok')

    def _is_after_restore(self):
        return exists(self._restore_stamp)

    def _after_restore_string(self):
        if self._is_after_restore():
            return "restore"
        return "NO restore"

    def _set_restore_stamp(self, value):
        if not value:
            if exists(self._restore_stamp):
                unlink(self._restore_stamp)
            return

        with open(self._restore_stamp, 'w') as fd:
            fd.write("restoring")

    def signalAutoconf(self):
        self.config_manager.setApplyNeeded()

    def initialApplyIfNeeded(self):
        if not self.config_manager.isApplyNeeded():
            return
        responsible = Responsible(caller_component=self.name, action=INITIAL_APPLY)
        self.config_manager.setApplyNeeded(False)
        self.error("Initial application of autoconfigured modules (first ufwi-rpcd start)")
        return self.config_manager.apply(rotate=False, responsible=responsible)

    def formatServiceArguments(self, service, arguments):
        if service == 'set':
            arguments = ('***' for argument in arguments)
        return Component.formatServiceArguments(self, service, arguments)

    def registerConfigComponent(self, component, cb_modify, cb_apply, cb_rollback):
        """
        all config component must implement following methods:
            - a getAllDeps()
            - getConfigDepends()
        """
        callbacks = {
            'modify': cb_modify,
            'apply': cb_apply,
            'rollback': cb_rollback,
        }
        for event, method in callbacks.iteritems():
            self.core.config_manager.subscribe(
                method,
                component.NAME,
                component.getConfigDepends(),
                event,
                component.NAME
                )

    def setModified(self, component_name):
        print "FIXME: Component %s is modified" % component_name

