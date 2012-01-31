"""
Copyright (C) 2009-2011 EdenWall Technologies
Written by Victor STINNER <vstinner AT edenwall.com>
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

from errno import ENOENT
from logging import CRITICAL
from os.path import exists
from twisted.internet.defer import inlineCallbacks, returnValue

from ufwi_rpcd.backend.error import exceptionAsUnicode
from ufwi_rpcd.common.error import formatError
from ufwi_rpcd.common.human import humanRepr
from ufwi_rpcd.common.journal_messages import GLOBAL

from .states import IdleState

class ExitApplyConfig(Exception):
    def __init__(self, failure):
        self.failure = failure
        Exception.__init__(self, formatError(failure))

class Callbacks(object):
    def __init__(self, modify, apply, rollback):
        self.modify = modify
        self.apply = apply
        self.rollback = rollback

class ApplyConfig:
    def __init__(self, manager, responsible,  message, silent, callbacks):
        self.manager = manager
        self.journal = manager.application_journal
        self.responsible = responsible
        self.message = message
        self.silent = silent
        self.filenames = manager.filenames
        self.modify_callbacks = callbacks.modify
        self.apply_callbacks = callbacks.apply
        self.rollback_callbacks = callbacks.rollback

        paths = set()
        for items in self.apply_callbacks:
            for item in items[3]:
                paths.add(item)
        self.paths = paths

    def keysModified(self):
        """compute keys from paths"""
        keys = []
        for path in self.paths:
            key = path[1:] # remove '/'
            key = key.split('/')[0] # keep only component name
            keys.append(key)
        return keys

    def overrideconf(self, tmp_configuration):
        self.manager._running_configuration = tmp_configuration
        self.manager.running_sequence_number = self.manager.saved_sequence_number
        if not self.silent:
            self.manager.critical("New configuration succesfully applied")

    def writePathsFile(self):
        if self.paths is None:
            return
        seq_number = self.manager.saved_sequence_number
        paths = unicode(list(self.paths))
        try:
            with open(self.filenames.paths_file, 'a') as fd:
                fd.write("%s %s\n" % (seq_number, paths))
        except IOError, err:
            self.manager.writeError(err, "During apply")
            if err.errno != ENOENT:
                raise

    def writeLastWorking(self):
        self.filenames.configApply(self.message)

    @inlineCallbacks
    def success(self, tmp_configuration):
        if (
            self.responsible.has_no_diff()
            and exists(self.filenames.last_working)
            ):
            self.overrideconf(tmp_configuration)
            returnValue([])

        post_apply_errors = []
        try:
            yield self.writeLastWorking()
        except Exception, err:
            self.manager.writeError(err, "Error on saving the new configuration")
            post_apply_errors.append(exceptionAsUnicode(err))
        self.overrideconf(tmp_configuration)
        yield self.writePathsFile()
        returnValue(post_apply_errors)

    def __call(self, log_prefix, func, *args):
        self.manager.debug("%s: call %s" % (log_prefix, humanRepr(func)))
        return func(*args)

    def _call_apply(self, name, func, *args):
        self.journal.log_component_apply_fired(name)
        return self.__call("apply", func, *args)

    def _call_in_rollback(self, name, func, *args):
        return self.__call("rollback", func, *args)

    @inlineCallbacks
    def apply(self):
        if not self.apply_callbacks:
            return
        self.manager.info("Call apply callbacks")
        self.journal.log_apply_started()
        try:
            component_names = tuple(item[0] for item in self.apply_callbacks)
            self.journal.log_applied_component_list(component_names)
            for name, callback, callback_arg, paths in self.apply_callbacks:
                try:
                    yield self._call_apply(name, callback, self.responsible, callback_arg, paths)
                except Exception, err:
                    self.logApplyError(err, name, callback)
                    raise ExitApplyConfig(err)
        finally:
            self.journal.log_apply_ended()

    def logApplyError(self, err, name, callback):
        err_msg = formatError(err)

        message = "Apply error in %s - %s:\n %s" % (
            name,
            humanRepr(callback),
            err_msg
            )

        self.journal.log_apply_error(err_msg)
        self.manager.writeError(err, message, log_level=CRITICAL)

    def logRollbackError(self, failure, name, callback):
        message = "Rollback error in %s - %s" % (name, humanRepr(callback))
        self.manager.writeError(failure,
            message,
            log_level=CRITICAL)

        self.journal.log_rollback_error(formatError(failure))

        # continue to the next callback

    @inlineCallbacks
    def rollback(self, apply_error):
        if isinstance(apply_error, ExitApplyConfig):
            apply_error = apply_error.failure
        self.manager.error("Rollback")
        self.journal.log_rollback_started()


        yield self.manager.createDiagnosticFiles()
        yield self.manager.restoreLastWorking()

        # execute read config callbacks (read the old (restored) configuration)
        ok = True
        self.manager.info("Rollback: rereading configuration")
        #names sent: rollback callbacks.
        component_names = tuple(item[0] for item in self.rollback_callbacks)
        self.journal.log_rolled_back_component_list(component_names)
        for name, callback, callback_arg, paths in self.modify_callbacks:
            try:
                yield self._call_in_rollback(name, callback, self.responsible)
            except Exception, err:
                yield self.logRollbackError(err, name, callback)
                ok = False
                # continue to execute the next callbacks

        # execute rollback callbacks
        self.manager.info("Call rollback callbacks")
        for name, callback, callback_arg, paths in self.rollback_callbacks:
            try:
                self.journal.log_component_rollback_fired(name)
                yield self._call_in_rollback(name, callback, self.responsible, callback_arg, paths)
            except Exception, err:
                yield self.logRollbackError(err, name, callback)
                ok = False
                # continue to execute the next callbacks

        self.journal.log_rollback_ended()

        if ok:
            self.manager.critical("Rollback done: the last working configuration was successfully restored.")
        else:
            self.manager.critical("Rollback failure: unable to restore the previous configuration.")

    # FIXME: execute run() in a big try/except?
    # if rollback() raises a new error, it's not catched
    @inlineCallbacks
    def run(self, tmp_configuration):
        # returned value:
        #  - None         if there is nothing to apply (see apply method)
        #  - []           no error was encountered (see success method)
        #  - [err1, err2] errors were encountered (see rollback method)
        self.journal.log_global(GLOBAL)
        try:
            try:
                yield self.apply()
            except Exception, err:
                yield self.rollback(err)
                errors = [exceptionAsUnicode(err)]
            else:
                errors = yield self.success(tmp_configuration)
        finally:
            self.manager.enterState(IdleState, silent=self.silent)
        returnValue(errors)

