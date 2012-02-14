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

from ufwi_ruleset.common.rule import DefaultDecisions as BaseDefaultDecisions

class DefaultDecisions(BaseDefaultDecisions):
    def __init__(self, window, rule_type):
        ipv6 = (rule_type == "acls-ipv6")
        BaseDefaultDecisions.__init__(self, window.config, ipv6)
        self.server_support = window.compatibility.default_decisions
        self.ruleset = window.ruleset
        self.rule_type = rule_type

    def reset(self):
        self.decisions = {}

    def refresh(self):
        if not self.server_support:
            return
        decisions = self.ruleset('getDefaultDecisions', self.rule_type)
        self.importXMLRPC(decisions )

    def save(self):
        decisions = self.exportXMLRPC()
        return self.ruleset('setDefaultDecisions', self.rule_type, decisions)
