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
from ufwi_ruleset.forward.rule.acl import AclIPv4, AclIPv6
from ufwi_ruleset.forward.rule.default_decision import DefaultDecisions

class AclRules(Rules):
    def __init__(self, ruleset, default_decisions, xml_tag):
        Rules.__init__(self, ruleset, xml_tag)
        self.default_decisions = default_decisions

    def importXMLRules(self, rules, context, action):
        self.default_decisions.importXML(rules)
        Rules.importXMLRules(self, rules, context, action)

    def exportXMLRules(self, parent):
        empty = self.default_decisions.exportXML(parent)
        empty &= Rules.exportXMLRules(self, parent)
        return empty

class AclIPv4Rules(AclRules):
    RULE_CLASS = AclIPv4
    NAME = 'acls-ipv4'
    UPDATE_DOMAIN = u'acls-ipv4'
    UPDATE_CHAIN_DOMAIN = u'acls-ipv4-chains'

    def __init__(self, ruleset):
        default_decisions = DefaultDecisions(ruleset.config, False, "acls-ipv4-decisions")
        AclRules.__init__(self, ruleset, default_decisions, "acls_ipv4")

class AclIPv6Rules(AclRules):
    RULE_CLASS = AclIPv6
    NAME = 'acls-ipv6'
    UPDATE_DOMAIN = u'acls-ipv6'
    UPDATE_CHAIN_DOMAIN = u'acls-ipv6-chains'

    def __init__(self, ruleset):
        default_decisions = DefaultDecisions(ruleset.config, True, "acls-ipv6-decisions")
        AclRules.__init__(self, ruleset, default_decisions, "acls_ipv6")

