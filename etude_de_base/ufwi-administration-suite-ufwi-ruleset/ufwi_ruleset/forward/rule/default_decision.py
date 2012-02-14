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

from ufwi_rpcd.common.xml_etree import etree

from ufwi_ruleset.common.rule import (
    DefaultDecisions as BaseDefaultDecisions)
from ufwi_ruleset.forward.action import Action, ActionHandler, Update

class DefaultDecisions(BaseDefaultDecisions):
    def __init__(self, config, ipv6, domain):
        BaseDefaultDecisions.__init__(self, config, ipv6)
        self.domain = domain

    def _import(self, chain, node):
        decision = node.attrib.get('decision', '')
        if 'log' in node.attrib:
            log = (node.attrib['log'] == '1')
        else:
            log = False
        self.set(chain, decision, log)

    def importXML(self, rules):
        parent = rules.find("default_decisions")
        if parent is None:
            return
        node = parent.find("input")
        if node is not None:
            self._import('INPUT', node)
        node = parent.find("output")
        if node is not None:
            self._import('OUTPUT', node)
        for node in parent.findall('chain'):
            attr = node.attrib
            chain = (attr.get('input'), attr.get('output'))
            self._import(chain, node)

    def exportXML(self, rules):
        if not self.decisions:
            return True
        parent = etree.SubElement(rules, 'default_decisions')
        for key, decision_log in self.decisions.iteritems():
            decision, log = decision_log
            if key == 'INPUT':
                node = etree.SubElement(parent, 'input')
            elif key == 'OUTPUT':
                node = etree.SubElement(parent, 'output')
            else:
                node = etree.SubElement(parent, 'chain', input=key[0], output=key[1])
            node.attrib['decision'] = decision
            if log:
                node.attrib['log'] = '1'
        return False

    def _setDecisions(self, decisions):
        self.decisions = decisions

    def setDecisions(self, decisions):
        new_decisions = self._importXMLRPC(decisions)

        update = Update(self.domain, "update", -1)
        action = Action(
            ActionHandler(update, self._setDecisions, new_decisions),
            ActionHandler(update, self._setDecisions, self.decisions))
        return action

