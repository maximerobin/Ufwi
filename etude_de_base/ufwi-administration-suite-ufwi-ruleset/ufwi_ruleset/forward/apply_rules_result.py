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

from collections import defaultdict
from ufwi_rpcd.common import tr
from ufwi_ruleset.forward.error import RulesetError

class ApplyRulesResult:
    def __init__(self, logger, raise_error=False,
    ignore_consistency_error=False):
        self.logger = logger
        self.raise_error = raise_error
        self.ignore_consistency_error = ignore_consistency_error

        self.warnings = []
        self.errors = []
        self.applied = False

        # domain (str) => list of (rule B id (int), rule A id (int))
        self.consistency_warnings = defaultdict(list)
        self.consistency_errors = defaultdict(list)

    def info(self, format, *args):
        self.warnings.append((format, args))
        self.logger.info(format %args)

    def warning(self, format, *args):
        self.warnings.append((format, args))
        self.logger.warning(format %args)

    def error(self, format, *args):
        if self.raise_error:
            raise RulesetError(format, *args)
        self.errors.append((format, args))
        self.logger.error(format % args)

    def hiddenRule(self, rule_b, rule_a, is_blocker):
        duplicate = (rule_b.id, rule_a.id)
        key = rule_b.update_domain
        if is_blocker:
            messages = self.consistency_errors
        else:
            messages = self.consistency_warnings
        messages[key].append(duplicate)
        if self.ignore_consistency_error:
            func = self.warning if is_blocker else self.info
        else:
            func = self.error if is_blocker else self.warning
        func(tr("%s is hidden by %s"), unicode(rule_b), unicode(rule_a))

    def exportXMLRPC(self):
        return {
            'warnings': self.warnings,
            'errors': self.errors,
            'applied': self.applied,
            'consistency_warnings': dict(self.consistency_warnings),
            'consistency_errors': dict(self.consistency_errors),
        }

def filterRules(result, rules):
    newlist = []
    for rule in rules:
        if rule.checkRule(result):
            newlist.append(rule)
    return newlist

