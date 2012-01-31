#coding: utf-8
"""
$Id$


Copyright (C) 2009-2011 EdenWall Technologies

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


from logging import CRITICAL

from twisted.internet.defer import succeed
from twisted.python.failure import Failure
from ufwi_rpcd.common.error import reraise

class PrepareException(Exception):
    pass

class SaveException(Exception):
    pass

def executeTransactionsDefer(logger, transactions):
    """
    call _executeTransactions which is deferred compliant
    """
    exe = executeTransactions(logger, transactions)
    return exe.run()

class executeTransactions(object):
    """
    compliant with deferred : steps of Transaction can return a deferred
    """
    # Algorithm : see executeTransactions

    def __init__(self, logger, transactions):
        self.logger = logger
        self.transactions = transactions

    @staticmethod
    def execute(x, callback):
        """
        don't use lambda in loop
        """
        return callback()

    def run(self):
        defer = succeed(None)
        for transaction in self.transactions:
            defer.addCallback(self.execute, transaction.prepare)
        defer.addErrback(self.prepare_failed)

        for transaction in self.transactions:
            defer.addCallback(self.execute, transaction.save)
        defer.addErrback(self.save_failed)

        for transaction in self.transactions:
            defer.addCallback(self.execute, transaction.apply)

        defer.addBoth(self.afterApply) # PrepareException & SaveException -> next errback
        defer.addCallback(self.rollback)
        defer.addBoth(self.check_state, (PrepareException, SaveException))
        defer.addBoth(self.cleanup)    # PrepareException -> next errback

        return defer

    def prepare_failed(self, err):
        """
        raise a PrepareException
        """
        error = PrepareException((unicode(err.value)))
        msg = "Error in transaction at step : prepare"
        self.logger.writeError(err, msg, log_level=CRITICAL)
        reraise(error)

    def save_failed(self, err):
        """
        raise a SaveException if err.value is not a PrepareException
        """
        if isinstance(err.value, PrepareException):
            return err

        error = SaveException((unicode(err.value)))
        msg = "Error in transaction at step : save"
        self.logger.writeError(err, msg, log_level=CRITICAL)
        reraise(error)

    def afterApply(self, data):
        """
        if exception in apply do rollbac
        if exception before apply, transmit it
        """
        if isinstance(data, Failure):
            if isinstance(data.value, (PrepareException, SaveException)):
                return data
            # error during apply : rollbacks *must* be executed
            msg = "Error in transaction at step : apply"
            self.logger.writeError(data, msg, log_level=CRITICAL)
            return True
        else:
            # no error : rollbacks *must not* be executed
            return False

    def rollback(self, do_rollback):
        if do_rollback:
            defer = succeed(None)
            for transaction in self.transactions:
                defer.addCallback(self.execute, transaction.rollback)
                # eat error, do next rollback
                defer.addErrback(self.rollback_failed)
            return defer

    def rollback_failed(self, err):
        if isinstance(err.value, (PrepareException, SaveException)):
            return err

        msg = "Error in transaction at step : rollback"
        self.logger.writeError(err, msg, log_level=CRITICAL)

        # errors are not transmitted
        return None

    def check_state(self, data, possible_errors):
        """
        - check error type : log and eat only errors which are bugs
        - no error : transmit value
        """
        if isinstance(data, Failure):
            if not isinstance(data.value, possible_errors):
                msg = 'Error in transaction incoherent state'
                self.logger.writeError(data, msg, log_level=CRITICAL)
            else:
                return data
        else:
            return data

    def cleanup(self, data):
        """
        clean up is not done if error was encountered during prepare
        if one cleanup() raise an exception, other cleanup() are called
        """
        if isinstance(data, Failure) and isinstance(data.value, PrepareException):
            return data
        defer = succeed(None)
        for transaction in self.transactions:
            defer.addCallback(self.execute, transaction.cleanup)
            defer.addErrback(self.cleanup_failed)
        return defer

    def cleanup_failed(self, err):
        msg = "Error in transaction at step : cleanup"
        self.logger.writeError(err, msg, log_level=CRITICAL)
        # errors are not transmitted
        return None

