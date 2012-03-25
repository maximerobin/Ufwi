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

from ufwi_ruleset.forward.error import RulesetError

class TemplateInstanciation:
    def __init__(self, ruleset):
        self.generic_links = ruleset.generic_links
        self.resources = ruleset.resources
        self.user_groups = ruleset.user_groups
        self._replaced = []
        self.require_group_name = ruleset.config['nufw']['require_group_name']

    def __enter__(self):
        self.replace()

    def __exit__(self, exc_type, exc_value, traceback):
        self.restore()

    def replace(self):
        for type, links in self.generic_links.iteritems():
            if type in ("interfaces", "networks", "hosts"):
                self.replaceNetwork(links)
            elif type == "user_groups":
                self.replaceUserGroup(links)

    def replaceNetwork(self, links):
        for generic_id, physical in links.iteritems():
            if physical is None:
                continue
            try:
                generic = self.resources[generic_id]
            except RulesetError:
                # Ignore non-existent link
                continue
            if not generic.isGeneric():
                continue
            generic.setPhysical(physical)
            self._replaced.append(generic)

    def replaceUserGroup(self, links):
        for generic_id, physical in links.iteritems():
            if physical is None:
                continue
            try:
                generic = self.user_groups[generic_id]
            except RulesetError:
                # Ignore non-existent link
                continue
            if not generic.isGeneric():
                continue
            generic.setPhysical(physical)
            self._replaced.append(generic)

    def restore(self):
        for generic in self._replaced:
            generic.setGeneric()
        self._replaced = []

