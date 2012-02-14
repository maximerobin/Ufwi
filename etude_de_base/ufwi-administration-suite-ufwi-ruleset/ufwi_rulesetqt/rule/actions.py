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

class RuleActions:
    """
    Check available actions for an ACL:
    - create
    - clone
    - delete
    - edit
    - move_up
    - move_down
    """
    def __init__(self, rules, identifiers):
        read_only = rules.ruleset.read_only
        if (not read_only) and len(identifiers):
            editables = all(rules[identifier]['editable']
                for identifier in identifiers)
        else:
            editables = False
        self.create = not read_only
        self.delete = editables
        self.iptables = (0 < len(identifiers))
        if rules.rule_type != "nats":
            self.ldap = self.iptables
        else:
            self.ldap = False

        only_one = (len(identifiers) == 1)
        self.clone = only_one and (not read_only)
        moveup = False
        movedown = False
        moveat = False
        if only_one:
            rule = rules[identifiers[0]]
            chain = rules.getChain(rule)
            order = chain.index(rule)
            editable = rule['editable'] and (not read_only)

            self.create_before = editable
            self.create_after = not read_only

            if editable:
                if 0 < order:
                    previous = chain[order-1]
                    moveup = previous['editable']
                try:
                    next = chain[order+1]
                    movedown = next['editable']
                except IndexError:
                    pass
                moveat = chain.getFirstEditableOrder() != (len(chain) - 1)

        else:
            editable = False

            self.create_before = False
            self.create_after = False

        self.edit = editable
        self.move_up = moveup
        self.move_down = movedown
        self.move_at = moveat
