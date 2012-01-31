#coding: utf-8
"""
Copyright (C) 2009-2011 EdenWall Technologies
Written by Feth AREZKI <farezki AT edenwall.com>

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

from copy import deepcopy
from datetime import datetime
from functools import wraps
from logging import WARNING, CRITICAL
from os.path import exists as path_exists, join, basename
from threading import Lock
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.threads import deferToThread
import tarfile


from ufwi_rpcd.common import EDENWALL, tr
from ufwi_rpcd.common.download import decodeFileContent
from ufwi_rpcd.common.error import exceptionAsUnicode
from ufwi_rpcd.common.human import humanRepr
from ufwi_rpcd.common.journal_messages import GLOBAL_DONE, GLOBAL_APPLY_SKIPPED
from ufwi_rpcd.common.logger import LoggerChild

from ufwi_rpcd.backend.error import CONFIG_NO_SUCH_KEY
from ufwi_rpcd.backend.exceptions import (AlreadyApplying,
    ConfigError, DeletedKey)
from ufwi_rpcd.backend.variables_store import VariablesStore

from ufwi_rpcd.core.context import Context

from .application_journal import ApplicationJournal
from .apply_config import ApplyConfig, Callbacks
from .apply_lock import ApplyLock
from .configuration import (Configuration,
    INVALID_SEQUENCE_NUMBER, validateSequenceNumber)
from .filenames import VersionnedFilenames
from .responsible import Responsible, USER_APPLY, BOOTUP_APPLY
from .states import (IdleState, NotInitializedState, ApplicableState,
    DraftState, ApplyingState, ModifiedState)
from .subscriptions import Subscriptions, VIRTUAL_NODE

if EDENWALL:
    from .ha_prune import prune_ha

VALID_NEXT = {
    # new state => valid old states
    ApplicableState: (ApplyingState, DraftState, IdleState),
    ApplyingState: (IdleState,),
    DraftState: (ApplicableState, IdleState),
    IdleState: (DraftState, ApplicableState),
    NotInitializedState: (IdleState,),
}

LOCK_FILE_NAME = "apply.lock"

def modify_ext_conf(f):
    """must be used by components which have "external configuration"
    "external configuration" is configuration not handled by config"""
    @wraps(f)
    def modify_config(component, context, *args, **kwargs):
        with component.core.config_manager.begin(component, context) as cm:
            # FIXME can not use following line because match are not done on end node
            # See pathIterator and match method in subscriptions.py (#1729)
            # cm.set("virtual", component.NAME, True)
            cm.set(VIRTUAL_NODE, component.NAME, component.NAME, True)
            f(component, context, *args, **kwargs)
            log = "External configuration of '%s' modified by '%s'"
            cm.commit(log % (component.NAME, f.__name__))
    return modify_config

class ConfigurationManager(LoggerChild):
    def __init__(self, config_component, vardir):
        logger = config_component
        LoggerChild.__init__(self, logger)
        self.config_component = config_component

        lock_file = join(vardir, LOCK_FILE_NAME)
        self.apply_locker = ApplyLock(self, lock_file)

        self.state = NotInitializedState
        #invalid
        self.running_sequence_number = INVALID_SEQUENCE_NUMBER
        self.saved_sequence_number = None
        self.subscriptions = {}
        for item in ('modify', 'apply', 'rollback'):
            self.subscriptions[item] = Subscriptions(item)
        self.apply_needed = False
        self._lock = Lock()
        self.application_journal = ApplicationJournal(self)
        self.__booted_up = False

    def incSequenceNumber(self):
        if not validateSequenceNumber(self.running_sequence_number):
            self.running_sequence_number = 0
        if not validateSequenceNumber(self.saved_sequence_number):
            self.saved_sequence_number = self.running_sequence_number
        self.saved_sequence_number += 1
        self.info("saved configuration sequence number: %s" % self.saved_sequence_number)
        self.info("applied configuration sequence number: %s" % self.running_sequence_number)

    def initDone(self, loaded, filename):
        if loaded:
            self.warning("Config manager initialized from file %s" % filename)
        else:
            self.info("Config manager initialized empty")

    @inlineCallbacks
    def _boot_apply(self, responsible, filename):
        loaded = self.importXML()
        base_keys = set(self._modified_configuration.keys())
        if not loaded:
            self.info("There was no config to be loaded!")
            self.incSequenceNumber()
        else:
            self.info(
                "Loaded a ufwi-rpcd configuration with main keys: [%s] "
                "and sequence number %s" % (
                    ", ".join(base_keys),
                    self.saved_sequence_number
                )
                )
        #Are we in the middle of an apply?
        self.apply_interrupted = self.apply_locker.exists()

        if self.apply_interrupted:
            yield self._boot_continue_apply(responsible)
        else:
            yield self._boot_apply_and_import_saved(responsible, base_keys)
        self.initDone(loaded, filename)

    @inlineCallbacks
    def _boot_continue_apply(self, responsible):
        # import modifications before applying
        self.critical(
            "A previous application of the "
            "configuration has been interrupted!"
            )
        self.info(
                "Re-importing pending modifications to the configuration..."
                )
        yield deferToThread(
            self.importModifications,
            responsible
            )

        self.info(
            "Will apply pending modifications to the configuration "
            "as soon as all modules will have been loaded..."
            )

        yield self.setApplyNeeded()

    @inlineCallbacks
    def _boot_apply_and_import_saved(self, responsible, base_keys):

        assert hasattr(self, '_modified_configuration'), "missing attribute '_modified_configuration'"
        assert base_keys == set(self._modified_configuration.keys()), \
            "We read base keys: [%s] and modified keys are [%s]" % (
                ", ".join(base_keys),
                ", ".join(self._modified_configuration.keys())
            )
        assert self.state == ApplicableState, "state must be ApplicableState"

        yield self.apply(rotate=False, responsible=responsible, silent=True)

        assert self.state == IdleState, "state must be IdleState"
        assert not hasattr(self, '_modified_configuration'),  "missing attribute '_modified_configuration'"
        assert base_keys == set(self._running_configuration.keys()), \
            "We read base keys: [%s] while importing, and now we have [%s]" % (
                ", ".join(base_keys),
                ", ".join(self._running_configuration.keys())
            )

        yield deferToThread(
            self.importModifications,
            responsible
            )

    @inlineCallbacks
    def initializeConfig(self, versionning_component, filename):
        """
        If we are rebooting in the middle of an apply(), we'll replay it.
        """
        self.warning("Initializing the configuration")
        responsible = Responsible(caller_component='config', action=BOOTUP_APPLY)
        self.filenames = VersionnedFilenames(filename, versionning_component)
        self.clear(silent=True)

        try:
            yield self._boot_apply(responsible, filename)
        except Exception, err:
            self.manageImportError(err)
            self.initDone(False, filename)

    def setApplyNeeded(self, value=True):
        self.apply_needed = value

    def isApplyNeeded(self):
        return self.apply_needed

    def manageImportError(self, err):
        self.writeError(err,
            "Error while reading configuration. No configuration loaded (modules will load defaults or autoconf)",
            log_level=WARNING)
        self.incSequenceNumber()
        self.clear()

    def clear(self, silent=True, change_state=True):
        self._running_configuration = Configuration()
        if change_state:
            self.enterState(IdleState, silent=silent)
        assert len(self._running_configuration) == 0

    def restoreLastWorking(self):
        if path_exists(self.filenames.last_working):
            # Load the last working configuration
            self.info("Restore last working configuration")
            if hasattr(self, '_modified_configuration'):
                self._modified_configuration.clear()
            self._running_configuration.clear()
            self._running_configuration.load(self.filenames.last_working)
            self.running_sequence_number = self._running_configuration.sequence_number
            self.saved_sequence_number = self.running_sequence_number
        else:
            self.info("No working configuration: clear the configuration")
            self.clear(change_state=False)
        self.filenames.rollback()

    @inlineCallbacks
    def commit(self, message, svn_commit=True, responsible=None):
        """
        Values that have been set can be either committed or reverted.

        return a deferred
        """
        assert not issubclass(self.state, NotInitializedState)
        assert self.state is DraftState

        # Prepare the message
        if responsible:
            trace = responsible.trace_message()
        else:
            trace = '-no trace-'
        message = "[COMMIT] %s #%s" % (trace, message)
        self.warning("Commit: %s" % message)

        if hasattr(self, "_draft_configuration"):
            self._draft_configuration.override(self._modified_configuration)

        self.incSequenceNumber()

        if svn_commit:
            #save a diff
            self.debug(
                "Saving pending modifications as %s (candidate)." %
                basename(self.filenames.save_diff_candidate)
                )
            self._modified_configuration.save(
                self.filenames.save_diff_candidate,
                self.saved_sequence_number
                )

            #Build a full candidate config
            saved_config = deepcopy(self._running_configuration)
            self.debug(
                "Pending modifications override a copy of the running config..."
            )
            self._modified_configuration.override(saved_config, propagate_deleted_keys=False)
            #save it
            self.debug(
                "...and we save this copy as %s (candidate)." %
                basename(self.filenames.save_candidate)
                )
            saved_config.save(self.filenames.save_candidate, self.saved_sequence_number)

            self.filenames.rotateCommit(message)

        # FIXME: use self._draft_configuration instead of self._modified_configuration?
        callbacks = self._reread_callbacks(responsible, self._modified_configuration)
        yield self.enterState(ApplicableState)
        yield self._callReread("commit", responsible, callbacks)

    def _reread_callbacks(self, responsible, changed_configuration):
        """
        returns a deferred
        """
        if changed_configuration is None:
            changed_configuration = ('/',)

        match_all = responsible.implies_full_reload()

        return self.subscriptions['modify'].match(
            changed_configuration,
            match_all=match_all
            )

    @inlineCallbacks
    def _callReread(self, action_name, responsible, callbacks):
        """
        returns a deferred
        """
        for name, callback, callback_arg, paths in callbacks:
            #drop callback args, they are not used
            try:
                self.debug("%s: call %s" % (action_name, humanRepr(callback)))
                yield callback(responsible)
            except Exception, failure:
                self.writeError(failure,
                    "Error on %s in %s" % (action_name, humanRepr(callback)),
                    log_level=CRITICAL)

    @inlineCallbacks
    def remoteLoad(self, responsible, paths):
        """
        Read configuration.xml (applied configuration written by nurestore)
        and enters applicable state.

        paths: list paths which have been modified since last application
               None for '/' (all) or an iterable which contains paths

        return a deferred
        """

        # enforce correct usage of api
        if isinstance(paths, basestring):
            raise ValueError("'paths' parameter must be None or iterable of"
                " strings (was : '%s')", type(paths))

        self.warning("Remote load")
        # importXML() sets state to ApplicableState
        # and load configuration in self._modified_configuration
        loaded = self.importXML(silent=False)

        assert loaded

        base_keys = list(self._modified_configuration.keys())
        base_keys.sort()
        self.debug(
            "Loaded a remote configuration with main keys [%s] "
            "and sequence number %s" % (
                ", ".join(base_keys),
                self._modified_configuration.sequence_number
            )
            )

        self._running_configuration.load(self.filenames.applied)

        #begin HA INCREMENTAL SYNC SPECIFIC
        # keep only effective modifications in self._modified_configuration
        if not base_keys:
            self.debug("Loaded empty configuration !")
            if paths:
                self.critical("Incoherent state: configuration is empty but "
                    "modified keys used ('%s')" % paths)
        elif paths:
            self.debug("Loaded a configuration with the following main keys "
                "(* indicates modification):")
            if not set(base_keys).intersection(paths):
                self.critical("Incoherent state: loaded configuration doesn't "
                " contain any key which are modified. Entire configuration "
                "will be reloaded")
            for key in base_keys:
                if key in paths:
                    self.debug("* %s" % key)
                else:
                    del self._modified_configuration[key]
        #end HA INCREMENTAL SYNC SPECIFIC
                    self.debug("  %s" % key)

        if EDENWALL and responsible.implies_prune_ha():
            prune_ha(self.config_component, self)

        # forget running configuration :
        # running conf must not be merged with modified configuration
        #
        # self._running_configuration.clear() useless because overwritten below
        # call to self.clear(change_state=False) is useless for same reason

        callbacks = self._reread_callbacks(responsible, self._modified_configuration)
        yield self._callReread("remoteLoad", responsible, callbacks)

    @inlineCallbacks
    def reset(self, responsible):
        """
        Clears all pending modifications to the running configuration

        return a deferred
        """
        self.warning("Reset")

        if responsible.implies_saved_config_on_hold():
            #We need to backup a saved config if there is any
            self._backup_saved_config(responsible)

        self.filenames.removeSavedFiles("Reset configuration")

        if self.state is IdleState:
            return
        self.saved_sequence_number = self.running_sequence_number
        callbacks = self._reread_callbacks(responsible, self._modified_configuration)
        self.enterState(IdleState)
        yield self._callReread("reset", responsible, callbacks)

    def _apply_message(self, responsible):
        if responsible is not None:
            message = "[APPLY] %s" % responsible.trace_message()
        else:
            responsible = Responsible(action=USER_APPLY)
            message = "[APPLY]"
        self.warning("Apply: %s" % message)
        return message

    def _apply_prepare(self, responsible):
        boot = (responsible.action == BOOTUP_APPLY)
        if boot:
            if self.__booted_up:
                raise ConfigError("You cannot bootup the config twice")
            self.__booted_up = True

        responsible.setjournal(self.application_journal)

        if not self.canApply(responsible):
            return False

        if not boot:
            self.critical("Applying new configuration")
        else:
            self.warning("Applying configuration")
        self.enterState(ApplyingState)

        return True

    @inlineCallbacks
    def apply(self, responsible=None, rotate=True, silent=False):
        """
        All pending modifications are merged into a configuration,
        and any component claiming a modified block will be notified (with its own apply() method).

        If a component's apply() fails, all changes since the last call to the present method are
        discarded and modules are notified again to apply the previous configuration.

        return deferred, with parameter:
            - None if can not apply
            - if apply is possible, a list with Errors (if any)
        """

        if not self._apply_prepare(responsible):
            self.application_journal.log_global(GLOBAL_APPLY_SKIPPED)
            returnValue([])

        message = self._apply_message(responsible)

        if not self._running_configuration:
            self.debug("No running configuration known yet. Will only use saved if it exists.")
            tmp_configuration = deepcopy(self._modified_configuration)
        else:
            tmp_configuration = deepcopy(self._running_configuration)
            self.debug(
                "Pending modifications override a copy of the running config..."
            )
            self._modified_configuration.override(tmp_configuration, propagate_deleted_keys=False)

        if rotate:
            self.debug(
                "Future configuration saved as %s" %
                basename(self.filenames.saved)
                )
            tmp_configuration.save(self.filenames.saved, self.saved_sequence_number)
            self.debug(
                "Saving pending modifications as %s" %
                basename(self.filenames.saved_diff)
                )
            self._modified_configuration.save(self.filenames.saved_diff, self.saved_sequence_number)

        self.info("Application for reason: %r" % responsible.action)
        match_all = responsible.implies_full_reload()
        if match_all:
            responsible.feedback(tr("Reloading full configuration"))

        callbacks = Callbacks(*tuple(
                    self.match(event, match_all)
                    for event in 'modify apply rollback'.split())
            )

        apply_config = ApplyConfig(self, responsible, message, silent, callbacks)

        try:
            errors = yield apply_config.run(tmp_configuration)

            if errors is None:
                self.debug('Apply - configModified signal not emitted')
            elif not errors:
                config_keys = apply_config.keysModified()
                if config_keys:
                    self.debug('Apply - configModified signal emitted')
                    sender = self.config_component.NAME
                    yield self.config_component.core.notify.emit(sender,
                        'configModified', config_keys=config_keys)
                elif responsible.action != BOOTUP_APPLY:
                    self.critical("Apply - can not emit 'configModified' signal, "
                        "unable to compute which composants have been modified")
            else:
                self.debug('Apply - configModified signal not emitted : errors')

            returnValue(errors)
        finally:
            if responsible.implies_saved_config_on_hold():
                #We need to restore an eventual backup of the saved config
                self._restore_saved_config(responsible)
            self.application_journal.log_global(GLOBAL_DONE)

    def canApply(self, responsible):
        """
        return True if application is possible
        else return False and log why application is not allowed
        """
        if issubclass(self.state, IdleState):
            responsible.warning(tr("No changes saved: there is nothing to apply"))
            return False

        if issubclass(self.state, ApplyingState):
            raise AlreadyApplying("Already applying, I am not going to apply anything more by now.")

        #This assert prevents applying if there are modifications pending. Commenting it drops these
        if not issubclass(self.state, ApplicableState):
            raise ConfigError("Cannot apply in state %s" % self.state.__name__)

        # don't allow user application if node is not active
        if responsible.action == USER_APPLY and self.ha_enabled() and not self.ha_node_active(responsible):
            responsible.warning(tr("Can not apply configuration: "
                "high availability is enabled and node is not active"))
            return False

        return True

    def ha_enabled(self):
        """return true if ha is enabled"""

        var_dir = self.config_component.core.config.get('CORE','vardir')
        ha_type_path = join(var_dir, 'ha_type')

        try:
            with open(ha_type_path) as f:
                ha_type = f.readline().strip()
                if ha_type in ('PRIMARY', 'SECONDARY'):
                    # ha enabled
                    self.debug("High Availability enabled: '%s'" % ha_type)
                    return True
        except Exception, err:
            self.debug("High Availability not enabled ('%s: %s')"
                % (ha_type_path, exceptionAsUnicode(err)))

        return False

    def ha_node_active(self, responsible):
        """return true if node is active, ha_enabled should be called first"""
        var_dir = self.config_component.core.config.get('CORE','vardir')
        ha_status_path = join(var_dir, 'ha_status')

        try:
            with open(ha_status_path) as f:
                ha_status = f.readline().strip()
                if ha_status in ('ACTIVE', 'INACTIVE'):
                    self.debug("High Availability node status: '%s'" % ha_status)
                    return ha_status == 'ACTIVE'
                else:
                    # unknow state
                    msg = tr("Unknow High Availability status (%(STATUS)s), "
                        "node is considered active")
                    responsible.warning(msg, STATUS=ha_status)
                    return True
        except Exception, err:
            self.writeError(err, title='Can not read HA status, '
                'asssume node is active')
            return True

    def revert(self, responsible=None):
        """
        Values that have been set can be either committed or reverted.
        """
        self.rollback(responsible)

    def rollback(self, responsible=None):
        if issubclass(self.state, (ApplicableState, ApplyingState, IdleState)):
            return
        assert issubclass(self.state, DraftState)
        self.state._revert(self)
        self.enterState(ApplicableState)

    @inlineCallbacks
    def createDiagnosticFiles(self):
        """
        if rollback save diagnostic files (if option specified)
        """
        try:
            yield self._createDiagnosticFiles()
        except Exception, err:
            self.writeError(err,
                "Error of the creation of rollback diagnostic files",
                log_level=WARNING)

    @inlineCallbacks
    def _createDiagnosticFiles(self):
        core = self.config_component.core
        save_diag = False
        if not core.config.has_option('CORE','rollback_save_diag'):
            return

        try:
            save_diag = core.config.get('CORE','rollback_save_diag')
            self.debug("'rollback_save_diag' option: %s" % save_diag)
        except ValueError:
            self.warning("invalid value for option 'rollback_save_diag' in section 'CORE'")

        if not save_diag:
            return

        context = Context.fromComponent(self.config_component)
        diag = yield core.callService(context, 'tools', 'getDiagnosticFile')

        var_dir = core.config.get('CORE','vardir')
        date = datetime.today()
        date = date.strftime("%y_%m_%d_%Hh%Mm%Sd")

        filename = "diag_%s.tar.gz" % date
        filename = join(var_dir, 'ufwi_conf', filename)
        self.debug("save diagnostic file to '%s'" % filename)
        with open(filename, 'wb') as fd:
            fd.write(decodeFileContent(diag))

        conf_name = "conf_%s.tar.gz" % date
        conf_name = join(var_dir, 'ufwi_conf', conf_name)
        tar = tarfile.open(conf_name, 'w:gz')
        tar.add('/etc')
        tar.close()

    def _get(self, path, default, fake_state=None):
        try:
            value = self.getValue(fake_state=fake_state, *path)
            if default is None:
                return value
            if isinstance(default, bool):
                return bool(int(value))
            elif isinstance(default, (int, long)):
                return int(value)
            elif isinstance(default, (unicode, str)):
                return unicode(value)
            else:
                raise TypeError("Invalid type for default value: %s"
                    % type(default))
        except ConfigError:
            if default is not None:
                return default
            else:
                raise

    def __contains__(self, *path):
        try:
            self.get(path)
            return True
        except ConfigError:
            return False

    def getKeys(self, *path):
        return set(self.get(*path))

    def get(self, *path, **kw):
        assert 'which_configuration' not in kw
        fake_state = kw.get('fake_state')
        if len(path) > 0 and isinstance(path[-1], dict):
            defaults = path[-1]
            parent = path[:-1]
            values = {}
            for key, default_value in defaults.iteritems():
                path = parent + (key,)
                values[key] = self._get(path, default_value, fake_state=fake_state)
            return values
        else:
            result = self._get(path, kw.get('default'), fake_state=fake_state)
            return result

    def _set(self, *path_and_value):
        path = [unicode(arg) for arg in path_and_value[:-2]]
        key = unicode(path_and_value[-2])
        value = path_and_value[-1]

        block = self._draft_configuration

        for item in path:
            try:
                # If block is a scalar, it doesn't have any alwaysGet method.
                block = block.alwaysGet(item)
            except AttributeError:
                raise ConfigError("You are trying to replace a scalar value with a dict, which is not supported. If this is really what you want, delete it first")
        block[key] = value

    def set(self, *path):
        self.enterState(DraftState)
        parent = path[:-1]
        new_value = path[-1]
        if len(parent) < 2 and isinstance(new_value, (str, unicode, int, float)):
            raise ConfigError("unexpected structure: only storages are expected at level 0 (no litteral)")
        if isinstance(new_value, dict):
            if len(new_value) == 0:
                set_path = parent + ({}, )
                self._set(*set_path)
                return
            for parent, key, value in self._getLeafs(*path):
                set_path = parent + (key, value)
                self._set(*set_path)
        else:
            path_and_value = parent + (path[-1],)
            self._set(*path_and_value)

    def _getLeafs(self, *path):
        recursive_dict = path[-1]
        path = path[:-1]
        assert isinstance(recursive_dict, dict), recursive_dict
        for key, value in recursive_dict.iteritems():
            if isinstance(value, dict):
                recursive_path = path + (key, value)
                for final_path, final_key, final_value in self._getLeafs(*recursive_path):
                    yield final_path, final_key, final_value
            else:
                yield path, key, value

    def getOrderedKeys(self, *path):
        result = list(self.getKeys(*path))
        result.sort()
        return result

    def orderedItems(self, *path):
        for key in self.getOrderedKeys(*path):
            value_path = list(path)
            value_path.append(key)
            yield key, self.getValue(*value_path)

    def items(self, *path):
        for key in self.getKeys(*path):
            value_path = path + (key, )
            yield key, self.getValue(*value_path)

    def listValues(self, *path):
        for key, value in self.items(*path):
            yield value

    def delete(self, *path):
        """
        Deletes any value under this path.
        Enters DraftState (meaning you have to commit)
        """
        #Raise an error if this does not exist
        self.get(*path)

        #Go to a state in which we modify
        self.enterState(DraftState)

        #actually modify
        self.state._delete(self, *path)

    # apply and rollback callback prototype:
    #   def callback(responsible, callback_arg, paths): ...
    #
    # modify callback prototype:
    #   def callback(responsible): ...
    def subscribe(self, callback, name, depends_on, event, *path):
        subscriptions = self.subscriptions[event]
        subscriptions.addSubscriber(callback, name, depends_on, *path)

    def exportXML(self, filename):
        self.debug('exporting configuration to %s' % filename)
        self._running_configuration.save(filename, self.running_sequence_number)

    def importXML(self, silent=False):
        filename = self.filenames.applied
        if not silent:
            self.debug('importing configuration from %s' % filename)
        return self._load(filename, silent)

    def loadSavedConfig(self):
        filename = self.filenames.saved_diff
        self.info('importing MODIFIED configuration from %s' % filename)
        return self._load(filename)

    def _load(self, filename, silent=False):
        self.enterState(ApplicableState, silent=silent)
        if path_exists(filename):
            self._modified_configuration.load(filename)
            self.saved_sequence_number = self._modified_configuration.sequence_number
            return True
        else:
            return False

    def importModifications(self, responsible):
        """
        return a deferred
        """
        filename = self.filenames.saved_diff
        if not path_exists(filename):
            self.debug("No pending modifications to re-import")
            return

        partial_configuration = Configuration()
        try:
            partial_configuration.load(filename)
            sequence_number = partial_configuration.sequence_number
            self.debug(
                "Found pending modifications with sequence nb: %s" %
                sequence_number
                )
        except Exception, err:
            self.writeError(err, "Error on importing modifications", log_level=CRITICAL)
            self.filenames.removeDiff("Dropping invalid file.")
            return

        return self.loadSavedConfig()

    def enterState(self, state, silent=False):
        """
        Casual enterState method: leaves previous state, enter new state.
        """
        if self.state is state:
            #Not changing state
            self.debug("State not changed, new state is current state")
            return

        if self.state in VALID_NEXT:
            if state not in VALID_NEXT[self.state]:
                successors = [successor.NAME for successor in VALID_NEXT[state]]
                raise ConfigError(
                    "cannot enter %s from %s. Authorized: %s"
                    % (state.NAME, self.state.NAME, successors))

        with self._lock:
            if state is ApplyingState:
                self._enterApplyingState()
            elif self.state is ApplyingState:
                self._exitApplyingState()

            self.debug("Change state from %s to %s" % (self.state.__name__, state.__name__))
            self.state.exit(self, state, silent=silent)
            state.enter(self, silent=silent)

    def _enterApplyingState(self):
        if self.apply_locker.exists() and not self.apply_interrupted:
            raise ConfigError("ApplyingState lockfile already exists")
        self.apply_locker.create()

    def _exitApplyingState(self):
        if not self.apply_locker.exists():
            self.critical("ApplyingState lockfile does not exist. "
            "While exiting 'Applying State'")

        self.apply_locker.delete()
        self.apply_interrupted = False

    def getValue(self, *path, **kw):
        fake_state = kw.get('fake_state')
        configurations = self._iterConfigurations(fake_state)
        result = None

        descent = True
        for configuration in configurations:
            if not descent:
                break
            try:
                recent_result = configuration.getValue(path)
            except DeletedKey:
                break
            except (KeyError, ConfigError):
                continue
            descent = not configuration.isPathDeleted(path)
            if isinstance(result, VariablesStore):
                if isinstance(recent_result, VariablesStore):
                    result.override(recent_result)
                    result = recent_result
                elif recent_result is not None:
                    continue
            elif result is not None:
                continue
            else:# isinstance(recent_result, VariablesStore):
                result = recent_result

        if result is None:
            raise ConfigError(CONFIG_NO_SUCH_KEY, "no such value: %s" % (unicode(path),))

        if isinstance(result, Configuration):
            result = result.toDict()
        return result

    def _iterConfigurations(self, fake_state):
        if fake_state is None:
            state = self.state
        else:
            state = fake_state

        if state == DraftState:
            yield self._draft_configuration
        if state in (DraftState, ApplicableState, ApplyingState):
            yield self._modified_configuration
        if state in (DraftState, ApplicableState, IdleState, ApplyingState):
            yield self._running_configuration

    def getConfigDiffSequenceNumber(self):
        return self.saved_sequence_number

    def getRunningConfigSequenceNumber(self):
        return self.running_sequence_number

    def isModified(self):
        return issubclass(self.state, ModifiedState)

    def match(self, event, match_all=False):
        """
        Supported events: 'modify', 'apply', 'rollback'.
        This is called by apply_config
        """
        subscriptions = self.subscriptions[event]

        if match_all:
            return subscriptions.match(None, match_all=True)

        elif self._modified_configuration:
            #This is a local application, we'll call modify_callbacks only
            #in the case of a rollback: they were triggered already by every config.set(...)
            return subscriptions.match(self._modified_configuration)
        #This is a remote application, we'll call modify_callbacks before apply_callbacks
        # TODO pass paths
        return subscriptions.match(('/',))

    def _backup_saved_config(self, responsible):
        responsible.feedback(tr(
            "Putting the saved configuration on hold if any."
            ))
        backup_done = yield deferToThread(self.filenames.backup_saved_config)
        if backup_done:
            responsible.feedback(tr("Put the saved configuration on hold"))
            return

        responsible.feedback(tr(
            "There was no saved configuration waiting for application."
            ))

    def _restore_saved_config(self, responsible):
        responsible.feedback(tr(
            "Restoring the saved configuration that was on hold, if any."
            ))

        restored = yield deferToThread(self.filenames.restore_saved_config)
        if restored:
            responsible.feedback(tr(
                "Restored the saved configuration that was on hold."
                ))
            self._load(self.filenames.saved_diff, silent=True)
            return

        responsible.feedback(tr(
            "There was no saved configuration waiting for application."
            ))

