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

from ufwi_rpcd.common.odict import odict
from ufwi_rpcd.common.tools import abstractmethod

from ufwi_rulesetqt.rule.nat import Nat
from ufwi_rulesetqt.rule.chain import (
    InputChain, OutputChain, ForwardChain,
    PreRoutingChain, PostRoutingChain)
from ufwi_rulesetqt.rule.default_decisions import DefaultDecisions
from ufwi_rulesetqt.model import Model

class RulesModel(Model):
    def __init__(self, window, rule_type, rule_class):
        Model.__init__(self, window, rule_type)
        self.compatibility = window.compatibility
        self.rule_type = rule_type
        self.name = rule_type
        self.rule_class = rule_class
        self.enabled = True

        # identifier (int) => AclIPv4, AclIPv6 or Nat object
        self.rules = {}

        # chain key => InputChain, OutputChain or ForwardChain
        # eg. chain=("eth0", "eth2") or chain="INPUT"
        self.chains = odict()

    def setEnabled(self, enabled):
        was_enabled = self.enabled
        self.enabled = enabled
        if self.enabled != was_enabled:
            if self.enabled:
                # use None because values are not used by refresh()
                self.refresh(None, None)
            else:
                self.clear()

    @abstractmethod
    def _createChain(self, key, rules=None):
        pass

    def _fillRuleChain(self, chain_key, new_rules):
        if isinstance(chain_key, list):
            chain_key = tuple(chain_key)
        new_rules = [self.rule_class(self.window, rule) for rule in new_rules]
        self.chains[chain_key] = self._createChain(chain_key, new_rules)
        for rule in new_rules:
            self.rules[rule['id']] = rule

    def refresh(self, all_updates, updates):
        if not self.enabled:
            return
        self.rules.clear()
        self.chains.clear()
        chains = self.ruleset('getRules', self.rule_type, append_fusion=True)
        for chain_key, rules in chains:
            self._fillRuleChain(chain_key, rules)

    def refreshChain(self, key):
        if not self.enabled:
            return
        if key in self.chains:
            for rule in self.chains[key]:
                del self.rules[rule['id']]
        new_rules = self.ruleset('getChain', self.rule_type, key, self.window.useFusion())
        self._fillRuleChain(key, new_rules)

    def refreshRule(self, rule_id):
        if not self.enabled:
            return
        # Get the current order in the chain
        old_rule = self.rules[rule_id]
        chain = self.chains[old_rule.createChainKey()]
        order = chain.index(old_rule)

        # Create the new rule
        data = self.ruleset('getRule', self.rule_type, rule_id, self.window.useFusion())
        new_rule = self.rule_class(self.window, data)

        # Register the new rule
        self.rules[new_rule['id']] = new_rule
        key = new_rule.createChainKey()
        if order is None:
            if key not in self.chains:
                self.chains[key] = self._createChain(key)
            self.chains[key].append(new_rule)
        else:
            self.chains[key][order] = new_rule
        return new_rule

    def removeChain(self, key):
        for rule in self.chains[key]:
            del self.rules[rule['id']]
        del self.chains[key]

    def clear(self):
        self.rules.clear()
        self.chains.clear()

    def __getitem__(self, identifier):
        return self.rules[identifier]

    def getChain(self, rule):
        key = rule.createChainKey()
        return self.chains[key]

class NatRulesModel(RulesModel):
    def __init__(self, window):
        RulesModel.__init__(self, window, "nats", Nat)
        self.clear()

    def clear(self):
        RulesModel.clear(self)
        self.chains[u'PREROUTING'] = PreRoutingChain()
        self.chains[u'POSTROUTING'] = PostRoutingChain()

    def _createChain(self, key, rules=None):
        if key == u'PREROUTING':
            return PreRoutingChain(rules)
        else: # key == u'POSTROUTING'
            return PostRoutingChain(rules)

class AclRulesModel(RulesModel):
    def __init__(self, window, rule_type, rule_class):
        RulesModel.__init__(self, window, rule_type, rule_class)
        self.default_decisions = DefaultDecisions(window, self.rule_type)

    def _createChain(self, key, rules=None):
        if key == u'INPUT':
            return InputChain(self, rules)
        elif key == u'OUTPUT':
            return OutputChain(self, rules)
        else:
            return ForwardChain(self, key[0], key[1], rules)

    def clear(self):
        RulesModel.clear(self)
        self.default_decisions.reset()

    def refresh(self, all_updates, updates):
        if not self.enabled:
            return
        RulesModel.refresh(self, all_updates, updates)
        self.default_decisions.refresh()

