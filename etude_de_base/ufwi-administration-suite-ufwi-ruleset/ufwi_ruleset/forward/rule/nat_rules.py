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

from ufwi_ruleset.forward.rule import Rules
from ufwi_ruleset.forward.rule.nat import NatRule
from ufwi_ruleset.forward.rule.chain import Chain

class NatRules(Rules):
    RULE_CLASS = NatRule
    NAME = 'nats'
    UPDATE_DOMAIN = u'nats'
    UPDATE_CHAIN_DOMAIN = u'nats-chains'

    def __init__(self, ruleset):
        Rules.__init__(self, ruleset, "nats")
        self.chains = {
            u'PREROUTING': Chain(u'PREROUTING'),
            u'POSTROUTING' : Chain(u'POSTROUTING')}

    def _deleteChain(self, chain, rule):
        chain.remove(rule)
        # don't remove empty NAT chain

    def itervalues(self):
        return self.acls.itervalues()

