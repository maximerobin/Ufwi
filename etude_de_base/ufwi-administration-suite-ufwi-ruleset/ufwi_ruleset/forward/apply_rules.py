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
from copy import deepcopy
import itertools

from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.threads import deferToThread

from ufwi_rpcd.common.transaction import executeTransactions

from ufwi_rpcd.backend import tr
from ufwi_rpcd.backend.logger import ContextLoggerChild

from ufwi_ruleset.config import PRODUCTION_RULESET
from ufwi_ruleset.common.rule import DefaultDecisions

from ufwi_ruleset.forward.apply_rules_result import ApplyRulesResult, filterRules
from ufwi_ruleset.forward.error import RulesetError
from ufwi_ruleset.forward.flatten import flattenObjectList
from ufwi_ruleset.forward.instanciation import TemplateInstanciation
from ufwi_ruleset.forward.iptables import WriteIptablesRules
from ufwi_ruleset.forward.last_ruleset import (lastRulesetApplied,
    SaveRuleset, ProductionRuleset)
from ufwi_ruleset.forward.ldap_rules import WriteLdapRules
from ufwi_ruleset.forward.match import aclsConsistencyTests
from ufwi_ruleset.forward.nuface_script import WriteRules, RulesetScript
from ufwi_ruleset.forward.ruleset import Ruleset
from ufwi_ruleset.forward.time_range import TimeRangeFileTransaction

from ufwi_ruleset.iptables.options import IptablesOptions

LOCK_RULESET = "ufwi_ruleset"

class ApplyRules:
    def __init__(self, context, component, ruleset, use_nufw,
    raise_error=False, only_consistency=False, consistency_error=False):
        self.context = context
        self.component = component
        self.ruleset = ruleset
        self.use_nufw = use_nufw
        self.only_consistency = only_consistency
        self.logger = ContextLoggerChild(context, component)
        self.result = ApplyRulesResult(self.logger, raise_error, not consistency_error)

        self.config = component.config
        self.lock_manager = component.core.lock_manager
        self.use_ipv6 = self.config['global']['use_ipv6']

        if ruleset:
            # Some consistency checks
            if self.use_nufw and (not self.ruleset.useNuFW()):
                raise RulesetError(tr("NuFW is disabled"))
            if not self.only_consistency and self.ruleset.is_template:
                raise RulesetError(tr("Unable to apply rules of a rule set template"))

            # Get rules
            self.acls_ipv4 = [acl for acl in self.ruleset.acls_ipv4 if acl.enabled]
            self.acls_ipv6 = [acl for acl in self.ruleset.acls_ipv6 if acl.enabled]
            self.nats = [nat for nat in self.ruleset.nats if nat.enabled]
            self.custom_rules = self.ruleset.custom_rules
            self.ruleset_name = self.ruleset.name
            self.ipv4_default_decisions = self.ruleset.acls_ipv4.default_decisions
            self.ipv6_default_decisions = self.ruleset.acls_ipv6.default_decisions
        else:
            # Apply localfw rules with no ruleset
            self.acls_ipv4 = tuple()
            self.acls_ipv6 = tuple()
            self.nats = tuple()
            self.custom_rules = None
            self.ruleset_name = None
            self.ipv4_default_decisions = DefaultDecisions(self.config, False)
            self.ipv6_default_decisions = DefaultDecisions(self.config, True)

    def consistencyEngine(self):
        for rules in (self.acls_ipv4, self.acls_ipv6):
            chain = []
            last_chain = None
            for rule in rules:
                new_chain = rule.createChainKey()
                if last_chain and last_chain != new_chain:
                    aclsConsistencyTests(chain, self.result)
                    chain = []
                chain.append(rule)
                last_chain = new_chain
            aclsConsistencyTests(chain, self.result)
        # TODO: test self.nats

    def _applyRulesThread(self):
        if self.only_consistency:
            self.consistencyEngine()
            return self.result.exportXMLRPC()
        elif not self.result.ignore_consistency_error:
            self.consistencyEngine()
            if self.result.consistency_errors:
                return self.result.exportXMLRPC()

        options = IptablesOptions()
        options.nufw = self.use_nufw

        if self.ruleset_name:
            self.logger.critical("Apply rules: rule set %r" % self.ruleset_name)
        else:
            self.logger.critical("Apply rules: no rule set (only localfw rules)")

        write_ldap = WriteLdapRules(self.logger, self.config['ldap'])

        ufwi_ruleset_rules = {
            'use_ipv6': self.use_ipv6,
            'use_nufw': self.use_nufw,
            'is_gateway': self.config.isGateway(),
        }
        if self.use_nufw:
            ufwi_ruleset_rules['ldap_config'] = self.config['ldap']
            if self.use_ipv6:
                acls = itertools.chain(self.acls_ipv4, self.acls_ipv6)
            else:
                acls = self.acls_ipv4
            ufwi_ruleset_rules['ldap_rules'] = write_ldap.createRules(acls)

        # TODO: disable IP forward at the beginning
        # TODO: FORWARD and INPUT: set policy to DROP

        # LDAP
        transactions = []
        if self.use_nufw:
            filename = self.config['nufw']['periods_filename']
            periods = TimeRangeFileTransaction(filename, self.acls_ipv4, self.acls_ipv6)
            transactions.append(periods)

        # iptables
        options.ipv6 = False
        write_iptables_ipv4 = WriteIptablesRules(
            self.logger, self.config, self.ipv4_default_decisions,
            self.acls_ipv4, self.nats, self.custom_rules,
            options, self.result)
        transactions.append(write_iptables_ipv4)

        ipv6_options = deepcopy(options)
        ipv6_options.ipv6 = True
        ipv6_options.deny_all = (not self.use_ipv6)
        write_iptables_ipv6 = WriteIptablesRules(
            self.logger, self.config, self.ipv6_default_decisions,
            self.acls_ipv6, None, self.custom_rules,
            ipv6_options, self.result)
        transactions.append(write_iptables_ipv6)

        # TODO: reload nuauth caches
        # TODO: reload nuauth periods

        # TODO: FORWARD and INPUT: set policy to ACCEPT

        write = WriteRules(self.logger, ufwi_ruleset_rules)
        transactions.append(write)

        script = RulesetScript(self.context, self.logger)
        transactions.append(script)

        save_ruleset = SaveRuleset(self.ruleset_name, self.use_nufw)
        transactions.append(save_ruleset)

        if self.ruleset \
        and (self.ruleset.filename != PRODUCTION_RULESET):
            production = ProductionRuleset(self.ruleset.filename)
            transactions.append(production)

        executeTransactions(self.logger, transactions)

        self.result.applied = True
        return self.result.exportXMLRPC()

    def _checkUserGroup(self, require_group_name, user_group):
        if require_group_name:
            if user_group.name is None:
                raise RulesetError(
                    tr('The firewall uses user group names, but the %s user group has no name'),
                    user_group.formatID())
        else:
            if user_group.group is None:
                raise RulesetError(
                    tr('The firewall uses user group numbers, but the %s user group has no number'),
                    user_group.formatID())

    def checkUserGroups(self):
        require_group_name = self.config['nufw']['require_group_name']
        user_groups = set()
        for rule in itertools.chain(self.acls_ipv4, self.acls_ipv6):
            user_groups |= set(flattenObjectList(rule.user_groups))
        for user_group in user_groups:
            self._checkUserGroup(require_group_name, user_group)

    def applyRules(self):
        if not self.only_consistency:
            self.lock_manager.acquire(self.context, "ufwi_ruleset_applyRules")
        try:
            if self.ruleset:
                with TemplateInstanciation(self.ruleset):
                    self.acls_ipv4 = filterRules(self.result, self.acls_ipv4)
                    self.acls_ipv6 = filterRules(self.result, self.acls_ipv6)
                    self.nats = filterRules(self.result, self.nats)
                    self.checkUserGroups()
                    if self.result.errors:
                        return self.result.exportXMLRPC()
                    return self._applyRulesThread()
            else:
                return self._applyRulesThread()
        finally:
            if not self.only_consistency:
                self.lock_manager.release(self.context, "ufwi_ruleset_applyRules")

@inlineCallbacks
def notifyIfApplied(result, component):
    if result['applied']:
        yield component.notify.emit(component.NAME, 'configModified')
    returnValue(result)

def applyRulesDefer(context, component, ruleset, use_nufw, consistency_error):
    if ruleset.isModified():
        raise RulesetError(
            tr("You have to save the rule set to apply the rules."))
    apply = ApplyRules(context, component, ruleset, use_nufw,
        consistency_error=consistency_error)
    defer = deferToThread(apply.applyRules)
    defer.addCallback(notifyIfApplied, component)
    return defer

def consistencyEngine(context, component, ruleset):
    apply = ApplyRules(context, component, ruleset, False,
        only_consistency=True, consistency_error=True)
    return deferToThread(apply.applyRules)

def reapplyLastRuleset(netcfg, context, component):
    logger = ContextLoggerChild(context, component)
    last_ruleset = lastRulesetApplied()

    if 'ruleset' in last_ruleset:
        name = last_ruleset['ruleset']
        message = "Reapply the last rule set: %s" % name
        ruleset = Ruleset(component, logger, netcfg)
        ruleset.load(logger, "ruleset", name, filename=PRODUCTION_RULESET)
        use_nufw = last_ruleset['use_nufw']
    else:
        message = "Reapply the last rule set: not rule set (only write localfw rules)"
        ruleset = None
        use_nufw = False
    logger.error(message)

    apply = ApplyRules(context, component, ruleset, use_nufw,
        raise_error=True, consistency_error=False)
    return apply.applyRules()
    # FIXME: add notifyIfApplied()

