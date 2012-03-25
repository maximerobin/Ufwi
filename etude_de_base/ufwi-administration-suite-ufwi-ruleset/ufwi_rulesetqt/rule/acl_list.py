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

from ufwi_rpcd.common import tr

from ufwi_rulesetqt.rule.list import RulesList
from ufwi_rulesetqt.rule.filter import RuleFilter, AttributeFilter
from ufwi_rulesetqt.rule.attr import (AclNetworks,
    AclFilters, AclOptions, AclComment, AclUsers)
from ufwi_rulesetqt.rule.actions import RuleActions
from ufwi_rulesetqt.rule.acl import AclIPv4, AclIPv6
from ufwi_rulesetqt.rule.model import AclRulesModel

from ufwi_ruleset.common.update import Updates

class UserGroupFilter(AttributeFilter):
    def match(self, rule, exact):
        if (not exact) and (not rule['user_groups']):
            return True
        return AttributeFilter.match(self, rule, exact)

class AclFilter(RuleFilter):
    def __init__(self, rules):
        RuleFilter.__init__(self, rules,
            tr("Drag & drop networks, protocols and user groups here"))
        getLibrary = rules.window.getLibrary
        self.filters.extend((
            AttributeFilter(self,
                getLibrary('resources'),
                'sources', 'destinations'),
            AttributeFilter(self,
                getLibrary('protocols'),
                'protocols'),
            UserGroupFilter(self,
                getLibrary('user_groups'),
                'user_groups'),
        ))

class AclList(RulesList):
    EDIT_STACK_INDEX = 1

    def __init__(self, window, model, table, widget_prefix):
        edit = window.edit_acl
        RulesList.__init__(self, window, model, table, model.rule_type, widget_prefix, edit)
        self.filter = AclFilter(self)

        config = self.window.config
        config.update_callbacks.append(self.updateConfig)

    def displayDecisions(self, updates, highlight=False):
        for row, chain in self.acl_headers.iteritems():
            self.fillHeader(row, chain)

    def updateConfig(self, config):
        self.displayDecisions(None)

    def setButtonsEnabled(self, identifiers=None):
        if identifiers is None:
            identifiers = self.currentAcls()
        actions = RuleActions(self, identifiers)
        self.getButton("create").setEnabled(actions.create)
        self.getButton("delete").setEnabled(actions.delete)
        self.getButton("edit").setEnabled(actions.edit)
        self.getButton("up").setEnabled(actions.move_up)
        self.getButton("down").setEnabled(actions.move_down)
        self.getButton("clone").setEnabled(actions.clone)

    def refreshChain(self, all_updates, updates):
        for update in updates:
            for chain_key, acl_id in update.identifiers:
                if isinstance(chain_key, list):
                    chain_key = tuple(chain_key)
                if update.type == "delete":
                    self.model.removeChain(chain_key)
                else:
                    self._refreshChain(chain_key)

    def fillAclRow(self, row, acl):
        rule_id = acl['id']
        users = AclUsers(self, rule_id, "user_groups", acl["user_groups"])

        if self.window.compatibility.platform:
            sources = acl["sources"] + acl["source_platforms"]
            destinations = acl["destinations"] + acl["destination_platforms"]
        else:
            sources = acl["sources"]
            destinations = acl["destinations"]

        sources = AclNetworks(self, rule_id, "sources", sources, True)
        destinations = AclNetworks(self, rule_id, "destinations", destinations, False)
        protocols = AclFilters(self, rule_id, "protocols", acl['protocols'], acl.getIcon(), acl['decision'])
        options = AclOptions(self, acl)
        comment = AclComment(self, acl)
        widgets = (
            users,
            sources,
            protocols,
            destinations,
            options,
            comment,
        )
        for column, widget in enumerate(widgets):
            if not acl['enabled']:
                widget.setEnabled(False)
            if acl['editable']:
                widget.setStyleSheet(u'font-weight: bold;')
            self.table.setCellWidget(row, column, widget)

    def getColumns(self):
        return [
            tr("User"), tr("Source"), tr("Decision"),
            tr("Destination"), tr("Advanced"), tr("Comment")]

    def _refreshChain(self, key):
        self.model.refreshChain(key)

    def refreshDecisions(self, all_updates, updates):
        self.model.default_decisions.refresh()

class AclIPv4List(AclList):
    RULES_STACK_INDEX = 0

    def __init__(self, window):
        model = AclRulesModel(window, "acls-ipv4", AclIPv4)
        AclList.__init__(self, window, model, window.acl4_table, "acl4")

class AclIPv6List(AclList):
    RULES_STACK_INDEX = 1

    def __init__(self, window):
        model = AclRulesModel(window, "acls-ipv6", AclIPv6)
        AclList.__init__(self, window, model, window.acl6_table, "acl6")
        self._setEnabled(self.window.config['global']['use_ipv6'])

    def _setEnabled(self, enabled):
        self.enabled = enabled
        self.window.main_tab.setTabEnabled(self.RULES_STACK_INDEX, self.enabled)
        self.model.setEnabled(self.enabled)

    def updateConfig(self, config):
        was_enabled = self.enabled
        self._setEnabled(config['global']['use_ipv6'])
        if self.enabled != was_enabled:
            self.display(Updates())
        else:
            AclList.updateConfig(self, config)

