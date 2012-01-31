
"""
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

from sys import exc_info
from ufwi_rpcd.common.human import humanRepr
from logging import CRITICAL

class Transaction(object):
    # First function called to prepare data
    # The function should not change the configuration
    def prepare(self):
        pass

    # Save the current state
    def save(self):
        pass

    # Apply changes
    # Call rollback() on error
    def apply(self):
        raise NotImplementedError()

    # Restore the previous state on error
    # Should not raise any exception
    def rollback(self):
        pass

    # Function always called after prepare()
    # Should not raise any exception
    def cleanup(self):
        pass

class TransactionsList:
    def __init__(self, transactions):
        self.transactions = transactions

    def prepare(self):
        for transaction in self.transactions:
            transaction.prepare()

    def save(self):
        for transaction in self.transactions:
            transaction.save()

    def apply(self):
        for transaction in self.transactions:
            transaction.apply()

    def rollback(self):
        for transaction in self.transactions:
            transaction.rollback()

    def cleanup(self):
        for transaction in self.transactions:
            transaction.cleanup()

def executeTransactions(logger, transactions):
    for transaction in transactions:
        transaction.prepare()
    try:
        for transaction in transactions:
            transaction.save()
        try:
            for transaction in transactions:
                try:
                    transaction.apply()
                except Exception, err:
                    # Log the error
                    logger.writeError(err,
                        "Transaction (%s) apply error" % humanRepr(transaction),
                        log_level=CRITICAL)
                    raise
        except Exception, err:
            # Keep the original error
            err_type, err_value, traceback = exc_info()

            # Rollback (catch rollback errors)
            logger.warning("Rollback transactions")
            for transaction in transactions:
                try:
                    transaction.rollback()
                except Exception, err:
                    logger.writeError(err,
                        "Transaction (%s) rollback error" % humanRepr(transaction),
                        log_level=CRITICAL)

            # Raise the original error
            raise err_type, err_value, traceback
    finally:
        for transaction in transactions:
            transaction.cleanup()


