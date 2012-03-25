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
from ufwi_ruleset.common.network import IPTABLES_TABLES
from ufwi_ruleset.forward.action import Action, ActionHandler, Update

class CustomRules(dict):
    XML_TAG = u"custom_rules"

    def __init__(self, ruleset):
        dict.__init__(self)
        self.ruleset=  ruleset

        for ipv in IPTABLES_TABLES:
            self[ipv] = {}
            for table in IPTABLES_TABLES[ipv]:
                self[ipv][table + '-post'] = u""
                self[ipv][table + '-pre'] = u""
        self.is_modified = False

    def importXML(self, root, context):
        custom_node = root.find(self.XML_TAG)
        if custom_node is None:
            return
        for ipv in IPTABLES_TABLES:
            for table in IPTABLES_TABLES[ipv]:
                for suffix in ('post', 'pre'):
                    xmltag = "%s-%s-%s" % (ipv, table, suffix)
                    node = custom_node.find(xmltag)
                    if (node is None) or (not node.text):
                        continue
                    self[ipv]["%s-%s" % (table, suffix)] = node.text

    def exportXML(self, root):
        custom_node = etree.SubElement(root, self.XML_TAG)
        empty = True
        for ipv in IPTABLES_TABLES:
            for table in IPTABLES_TABLES[ipv]:
                for suffix in ('post', 'pre'):
                    text = self[ipv]['%s-%s' % (table, suffix)]
                    if not text:
                        continue
                    rule = etree.SubElement(custom_node, '%s-%s-%s' % (ipv, table, suffix))
                    rule.text = text
                    empty = False
        if empty:
            root.remove(custom_node)

    def exportXMLRPC(self):
        return dict(self)

    def _setRules(self, rules):
        self.update(rules)

    def setRules(self, new_rules):
        old_rules = dict(self)
        updates = Update("custom_rules", "update", -1)
        action = Action(
            ActionHandler(updates, self._setRules, new_rules),
            ActionHandler(updates, self._setRules, old_rules))
        return self.ruleset.addAction(action)

