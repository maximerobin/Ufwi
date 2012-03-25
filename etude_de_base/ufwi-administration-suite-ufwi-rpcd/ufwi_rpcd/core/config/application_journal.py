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

$Id$
"""

from datetime import datetime
from time import time

from ufwi_rpcd.common.journal_messages import (ALL_MESSAGES,
    APPLIED_COMPONENT_LIST, APPLY_ERROR, ROLLBACK_ERROR, COMPONENT_APPLY_FIRED,
    COMPONENT_ROLLBACK_FIRED, PHASE_CHANGE, APPLYING, APPLYING_DONE,
    ROLLING_BACK, ROLLING_BACK_DONE, ROLLED_BACK_COMPONENT_LIST,
    COMPONENT_MESSAGE, GLOBAL_ERROR, GLOBAL_WARNING)
from ufwi_rpcd.common.logger import LoggerChild

class ApplicationJournal(LoggerChild):
    def __init__(self, logger):
        LoggerChild.__init__(self, logger)
        self.journal = None
        self.__current_component = None
        self.reset()

    def reset(self):
        self.journal = []
        self.__current_component = None

    def _addJournalEntry(self, message_type, content):
        timestamp = unicode(datetime.fromtimestamp(time()))

        if message_type not in ALL_MESSAGES:
            self.error("unknown message type : '%s' for message '%s'" %
                (message_type, content))
        self.journal.append((timestamp, message_type, content))

    def log_global(self, phase):
        self._addJournalEntry(PHASE_CHANGE, phase)

    def log_apply_started(self):
        self._addJournalEntry(PHASE_CHANGE, APPLYING)

    def log_apply_ended(self):
        self._addJournalEntry(PHASE_CHANGE, APPLYING_DONE)

    def component_info(self, message, **substitution):
        self.info(
            "[%s] %s" % (self.__current_component, message % substitution)
            )
        self._addJournalEntry(COMPONENT_MESSAGE, (message, substitution))

    def log_error(self, message, **substitution):
        self.error(message % substitution)
        self._addJournalEntry(GLOBAL_ERROR, (message, substitution))

    def log_warning(self, message, **substitution):
        self.warning(message % substitution)
        self._addJournalEntry(GLOBAL_WARNING, (message, substitution))

    def log_apply_error(self, message):
        self._addJournalEntry(APPLY_ERROR, message)

    def log_rollback_error(self, message):
        self._addJournalEntry(ROLLBACK_ERROR, message)

    def log_component_apply_fired(self, component_name):
        self._addJournalEntry(COMPONENT_APPLY_FIRED, component_name)
        self.__current_component = component_name

    def log_component_rollback_fired(self, component_name):
        self._addJournalEntry(COMPONENT_ROLLBACK_FIRED, component_name)
        self.__current_component = component_name

    def log_rollback_started(self):
        self._addJournalEntry(PHASE_CHANGE, ROLLING_BACK)

    def log_rollback_ended(self):
        self._addJournalEntry(PHASE_CHANGE, ROLLING_BACK_DONE)

    def log_applied_component_list(self, component_list):
        """
        signature allows for usage in a twisted deferred
        """
        self._addJournalEntry(APPLIED_COMPONENT_LIST, component_list)

    def log_rolled_back_component_list(self, component_list):
        self._addJournalEntry(ROLLED_BACK_COMPONENT_LIST, component_list)

    def getJournal(self, from_seq_nb):
        return self.journal[from_seq_nb:]

