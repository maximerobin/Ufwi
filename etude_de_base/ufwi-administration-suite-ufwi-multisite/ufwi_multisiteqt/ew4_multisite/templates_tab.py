
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

from PyQt4.QtCore import SIGNAL
from ufwi_rpcd.common import tr
from .groups_list import GroupsList
from .start_task import StartTask
from .edw_list import EdwList
from .multisite_tab import MultisiteTab

class TemplatesTab(GroupsList, MultisiteTab):
    HEADERS_ID = [ 'name', 'nuface_template', 'template_edition_time', 'links_validity', 'current_template', 'template_version', 'nuface_status', 'send_rules' ]
    FILTER_BY = [ 'name', 'nuface_template', 'current_template', 'nuface_status' ]
    GROUPS_BY_ID = [ 'nuface_template', 'current_template', 'nuface_status' ]
    ROLES = [ 'ruleset_read' ]
    LOCAL_ROLES = [ 'multisite_read' ]

    def __init__(self, client, scroll_area, main_window, edw_list, categories, categories_order):
        GroupsList.__init__(self, client, scroll_area, main_window.ui, EdwList, edw_list, categories, categories_order)
        self.start_task = StartTask(':/icons/apply_rules.png', 'Apply rules', self.sendRules, self, 'send_rules')
        self.ui = main_window.ui
        #self.connect(self.ui.actionUpdate_templates, SIGNAL('triggered()'), self.sendRules)
        self.connect(self.ui.actionUpdate_templates, SIGNAL('triggered()'), lambda: self.start_task.start(False))
        self.connect(self.ui.actionEdit_generic_links, SIGNAL('triggered()'), main_window.setupGenericLinks)

        self.template_list = []
        self.template_edition_date_dict = {}
        for edw in self.edw_list:
            edw.setTemplateList(self.template_list, self.template_edition_date_dict)

    def setTab(self):
        self.ui.actionUpdate_templates.setVisible(True)
        self.ui.actionEdit_generic_links.setVisible(True)
        self.ui.actionEdit_templates.setVisible(True)

    def unsetTab(self):
        self.ui.actionUpdate_templates.setVisible(False)
        self.ui.actionEdit_generic_links.setVisible(False)
        self.ui.actionEdit_templates.setVisible(False)

    def sendRules(self, sched_options):
        for edw in self.edw_list:
            edw.applyNufaceRules(sched_options)

    def refreshCells(self):
        rulesets = self.client.call("nuface", "rulesetList", "template")
        self.template_list = [unicode(tmpl[0]) for tmpl in rulesets]
        self.template_list.sort()
        self.template_list.insert(0, tr('No change'))
        self.template_list.insert(1, tr('None'))
        for tmpl in rulesets:
            self.template_edition_date_dict[unicode(tmpl[0])] = tmpl[1]

        for edw in self.edw_list:
            edw.setTemplateList(self.template_list, self.template_edition_date_dict)
            edw.refreshNuFaceData()

    def newObj(self, edw):
        edw.setTemplateList(self.template_list, self.template_edition_date_dict)
        GroupsList.newObj(self, edw)

    def createGroup(self, grp_name):
        GroupsList.createGroup(self, grp_name)
        self.grouped_tables[grp_name].edw_generic.setTemplateList(self.template_list, self.template_edition_date_dict)

