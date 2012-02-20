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
from ufwi_ruleset.forward.action import Action, ActionHandler, Update, Updates

class Fusion:
    def __init__(self, ruleset):
        self.resources = ruleset.resources
        self.user_groups = ruleset.user_groups

    def replace(self, generic_links, action=None, add_updates=False):
        # Clear current associations
        physical_objects = {
            'networks': {},
            'user_groups': {},
        }
        for network in self.resources:
            if not network.physical_object:
                continue
            physical_objects['networks'][network] = None
        for user_group in self.user_groups:
            if not user_group.physical_object:
                continue
            physical_objects['user_groups'][user_group] = None

        # Create new associations
        for type, links in generic_links.iteritems():
            if type == "interfaces":
                self.replaceNetwork(physical_objects['networks'], type, links)
            elif type == "user_groups":
                self.replaceUserGroup(physical_objects['user_groups'], links)

        # network and host resolver requires that
        # interfaces are already resolved
        for type, links in generic_links.iteritems():
            if type in ("networks", "hosts"):
                self.replaceNetwork(physical_objects['networks'], type, links)

        # Apply actions
        for key in ('networks', 'user_groups'):
            for generic, physical in physical_objects[key].iteritems():
                self.setPhysicalObject(generic, physical, action, add_updates)

    def setPhysicalObject(self, generic, physical_object, action, add_updates):
        old_physical = generic.physical_object
        if old_physical is physical_object:
            return
        if action:
            if add_updates:
                updates = Updates(Update(generic.update_domain, "update", generic.id))
                for ref in generic.references:
                    updates.addUpdate(Update(ref.update_domain, 'update', ref.id))
            else:
                updates = Updates()
            set_physical = Action(
                ActionHandler(updates, self._setPhysicalObject, generic, physical_object),
                ActionHandler(updates, self._setPhysicalObject, generic, generic.physical_object))
            action.executeAndChain(set_physical)
        else:
            self._setPhysicalObject(generic, physical_object)

    def replaceNetwork(self, physical_objects, link_type, links):
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

            # Find a corresponding physical object
            if link_type == 'interfaces':
                physical_object = self.resources.getInterfaceByName(physical)
            elif link_type == "networks":
                interface = generic.interface
                physical_object = interface.getNetworkByAddress(physical)
                interface = physical_objects.get(interface, interface.physical_object)
                if (not physical_object) and interface:
                    physical_object = interface.getNetworkByAddress(physical)
            else: # link_type == "hosts"
                interface = generic.interface
                physical_object = interface.getHostByAddress(physical)
                interface = physical_objects.get(interface, interface.physical_object)
                if (not physical_object) and interface:
                    physical_object = interface.getHostByAddress(physical)
            physical_objects[generic] = physical_object

    def _setPhysicalObject(self, generic, physical):
        generic.physical_object = physical

    def replaceUserGroup(self, physical_objects, links):
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

            physical_object = self.user_groups.getUserGroup(physical)
            physical_objects[generic] = physical_object

