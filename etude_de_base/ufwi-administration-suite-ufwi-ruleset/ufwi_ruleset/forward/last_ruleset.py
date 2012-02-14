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

from datetime import datetime
from os import unlink
from os.path import join as path_join, exists
from shutil import copyfile

from ufwi_rpcd.common.transaction import Transaction

from ufwi_rpcd.backend.exceptions import ConfigError
from ufwi_rpcd.backend.variables_store import VariablesStore

from ufwi_ruleset.config import RULESET_DIR, PRODUCTION_RULESET
from ufwi_ruleset.forward.file import File, unlinkQuiet

STORAGE_FILENAME = path_join(RULESET_DIR, "last_ruleset.xml")

def lastRulesetApplied():
    # See ufwi_ruleset.productionRules() service for the documentation
    if not exists(STORAGE_FILENAME):
        return {}
    storage = VariablesStore()
    storage.load(STORAGE_FILENAME)
    timestamp = storage["timestamp"]
    data = {
        'timestamp': timestamp,
        'use_nufw': (storage['use_nufw'] == u'1')}
    if exists(PRODUCTION_RULESET):
        try:
            data['ruleset'] = storage["name"]
        except ConfigError:
            # Key doesn't exist
            pass
    return data

class SaveRuleset(Transaction):
    def __init__(self, name, use_nufw):
        Transaction.__init__(self)
        self.new_ruleset = {'timestamp': datetime.now(), 'ruleset': name, 'use_nufw': use_nufw}
        self.filename = STORAGE_FILENAME

    def setRuleset(self, name):
        self.new_ruleset['ruleset'] = name

    def save(self):
        self.old_ruleset = lastRulesetApplied()

    def _write(self, timestamp, use_nufw, ruleset=None):
        timestamp = unicode(timestamp)
        storage = VariablesStore()
        storage["timestamp"] = unicode(timestamp)
        if ruleset:
            storage["name"] = ruleset
        storage["use_nufw"] = unicode(int(use_nufw))
        storage.save(self.filename)

    def apply(self):
        self._write(**self.new_ruleset)

    def rollback(self):
        if self.old_ruleset:
            self._write(**self.old_ruleset)
        else:
            try:
                unlink(self.filename)
            except OSError:
                pass

class ProductionRuleset(Transaction):
    def __init__(self, new_ruleset):
        Transaction.__init__(self)
        self.filename = PRODUCTION_RULESET
        self.new_ruleset = new_ruleset
        self.old_production = File(self.filename + ".old", False)

    def save(self):
        self.old_production.copyFrom(self.filename)

    def apply(self):
        copyfile(self.new_ruleset, self.filename)

    def rollback(self):
        if self.old_production.exist:
            self.old_production.renameTo(self.filename)
        else:
            unlinkQuiet(self.filename)

    def cleanup(self):
        self.old_production.unlink(quiet=True)

