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

from __future__ import with_statement
import pickle
from os import umask
from subprocess import PIPE, STDOUT

from ufwi_rpcd.common.transaction import Transaction
from ufwi_rpcd.common.process import createProcess, waitProcess, readProcessOutput
from ufwi_rpcd.common.logger import LoggerChild

from ufwi_rpcd.backend import tr

from ufwi_ruleset.forward.error import RulesetError
from ufwi_ruleset.forward.config import RULES_FILENAME
from ufwi_ruleset.forward.file import File

SCRIPT = ("/usr/sbin/ufwi_ruleset", "apply")

# 5 minutes to apply iptables and LDAP rules should be enough
TIMEOUT = 5*60

class WriteRules(Transaction, LoggerChild):
    def __init__(self, logger, ufwi_ruleset_rules):
        LoggerChild.__init__(self, logger)
        self.ufwi_ruleset_rules = ufwi_ruleset_rules
        self.filename = RULES_FILENAME
        self.old_rules = File(self.filename + ".old", False)
        self.new_rules = File(self.filename + ".new", False)

    def prepare(self):
        self.info("Write new rules")
        umask(0077)
        with self.new_rules.open("wb") as fp:
            pickle.dump(self.ufwi_ruleset_rules, fp, pickle.HIGHEST_PROTOCOL)

    def save(self):
        self.info("Keep current rules")
        umask(0077)
        self.old_rules.copyFrom(self.filename)

    def apply(self):
        self.error("Write rules to disk")
        try:
            self.new_rules.renameTo(self.filename)
        except OSError:
            self.error("No new rules to rename.")

    def rollback(self):
        self.error("Restore old rules")
        try:
            self.old_rules.renameTo(self.filename)
        except OSError:
            self.error("No old rules to rename.")


    def cleanup(self):
        self.error("Remove temp files")
        try:
            self.old_rules.unlink(quiet=True)
        except OSError:
            self.error("No old rules to clean.")
        try:
            self.new_rules.unlink(quiet=True)
        except OSError:
            self.error("No new rules to clean.")

class RulesetScript(Transaction, LoggerChild):
    def __init__(self, context, logger):
        LoggerChild.__init__(self, logger)
        self.arguments = SCRIPT
        if context.hasRole("ufwi_rpcd_debug"):
            self.arguments += ("--debug",)

    def apply(self):
        process = createProcess(self, self.arguments, stdout=PIPE, stderr=STDOUT)
        exitcode = waitProcess(self, process, TIMEOUT)
        if exitcode:
            lines = readProcessOutput(process.stdout, 100)
            lines = u'\n\n' + u'\n'.join(lines)
            raise RulesetError(tr("Ruleset script error (exitcode %s):%s"),
                exitcode, lines)

