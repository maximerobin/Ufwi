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
from os import umask
from os.path import join

from ufwi_rpcd.common.transaction import Transaction
from ufwi_rpcd.common.logger import LoggerChild
from ufwi_rpcd.backend.logger import ContextLoggerChild

from ufwi_ruleset.iptables.options import IptablesOptions
from ufwi_ruleset.iptables.generator import IptablesGenerator
from ufwi_ruleset.iptables.restore import iptablesRestore
from ufwi_ruleset.iptables.save import loadKernelModules, iptablesSave
from ufwi_ruleset.iptables.acls import aclsRules
from ufwi_ruleset.iptables.nat import natsRules

from ufwi_ruleset.config import RULESET_DIR
from ufwi_ruleset.forward.instanciation import TemplateInstanciation
from ufwi_ruleset.forward.file import File
from ufwi_ruleset.forward.apply_rules_result import ApplyRulesResult, filterRules

def iptablesRules(context, component, ruleset, rule_type, identifiers, use_nufw):
    logger = ContextLoggerChild(context, component)
    result = ApplyRulesResult(logger)

    # Not NAT rules in IPv6!
    if rule_type == 'nats':
        rules = ruleset.nats
        use_ipv6 = False
        default_decisions = None
    elif rule_type == 'acls-ipv6':
        rules = ruleset.acls_ipv6
        use_ipv6 = True
        default_decisions = rules.default_decisions
    else:
        rules = ruleset.acls_ipv4
        use_ipv6 = False
        default_decisions = rules.default_decisions
    if identifiers:
        rules = [ rules[id] for id in identifiers ]
    else:
        rules = rules

    options = IptablesOptions()
    options.format = "iptables"
    options.ipv6 = use_ipv6
    options.nufw = use_nufw

    with TemplateInstanciation(ruleset):
        rules = filterRules(result, rules)

        # Create iptables rules
        iptables = IptablesGenerator(logger, default_decisions, options, component.config, result)
        if rule_type != 'nats':
            lines = aclsRules(iptables, rules)
        else:
            lines = natsRules(iptables, rules, result)
        xmlrpc = result.exportXMLRPC()
        xmlrpc['iptables'] = [unicode(line) for line in lines]
        return xmlrpc

class WriteIptablesRules(Transaction, LoggerChild):
    def __init__(self, logger, config, default_decisions, acls, nats, custom_rules,
    options, apply_rules):
        LoggerChild.__init__(self, logger)
        self.generator = IptablesGenerator(logger, default_decisions, options, config, apply_rules)
        self.acls = acls
        self.nats = nats
        self.custom_rules = custom_rules
        self.options = options
        self.keep_files = True
        self.old_rules = None
        self.new_rules = None

    def prepare(self):
        self.info("Create the new iptables rules")
        umask(0077)
        filename = self.generator.writeRules(self.acls, self.nats, self.custom_rules)
        self.new_rules = File(filename, True)

    def save(self):
        self.info("Save the current iptables rules")
        loadKernelModules(self, self.options.ipv6)
        filename = iptablesSave(self, ipv6=self.options.ipv6)
        self.old_rules = File(filename, True)

    def apply(self):
        pass

    def rollback(self):
        self.error("Restore the old iptables rules")

        # Restore old rules
        iptablesRestore(self, self.old_rules.filename, ipv6=self.options.ipv6, check_error=False)

    def cleanup(self):
        if self.keep_files:
            return
        if self.old_rules:
            self.old_rules.unlink(quiet=True)
        if self.new_rules:
            self.new_rules.unlink(quiet=True)

class ApplyIptablesRules(Transaction, LoggerChild):
    def __init__(self, logger, use_ipv6):
        LoggerChild.__init__(self, logger)
        if use_ipv6:
            filename = 'new_rules_ipv6'
        else:
            filename = 'new_rules_ipv4'
        self.filename = join(RULESET_DIR, filename)
        self.use_ipv6 = use_ipv6

    def apply(self):
        iptablesRestore(self, self.filename, ipv6=self.use_ipv6)

