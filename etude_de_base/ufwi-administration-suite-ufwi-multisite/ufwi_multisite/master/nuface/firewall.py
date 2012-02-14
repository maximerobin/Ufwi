
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

import time
from copy import deepcopy
from ufwi_rpcd.core.context import Context
from ..common.firewall import MultiSiteFirewall
from task import RuleApplicationTask

class NuFaceFirewall(MultiSiteFirewall):
    ATTR = [ 'template', 'template_version', 'ruleset', 'association', 'last_sent', 'generic_links' ]

    TASK_CLS = RuleApplicationTask

    def __init__(self, component, core, module_name, name, attr):
        self.template = u''
        self.template_version = u''
        self.template_url = u''
        self.ruleset = u''
        self.association = u''
        self.generic_links = {}
        self.last_sent = 0
        MultiSiteFirewall.__init__(self, component, core, module_name, name, attr)

    def applyRules(self, sched_options, template, template_version, ruleset, association):
        self.template = template
        self.template_version = template_version
        self.ruleset = ruleset
        self.association = association
        self.last_sent = int(time.time())
        self.save()

        ctx = Context.fromComponent(self.component)
        task = RuleApplicationTask(self.core, ctx, self, sched_options, self.template, deepcopy(self.generic_links))
        self.setTask(task)

    def getGenericLinks(self):
        return self.generic_links

    def setGenericLinks(self, generic_links):
        # Delete links that have been deleted
        for type, assoc in self.generic_links.iteritems():
            for name in assoc.iterkeys():
                if name not in generic_links[type]:
                    self.component.config.delete('firewalls', self.name, 'generic_links', type, name)
        self.generic_links = generic_links
        self.save()


