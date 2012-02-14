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

from ufwi_rpcd.backend import tr
from ufwi_rpcd.common.tools import abstractmethod

from ufwi_ruleset.common.network import IPV6_ADDRESS, INTERFACE_ADDRESS

from ufwi_ruleset.forward.attribute import Boolean
from ufwi_ruleset.forward.error import RulesetError
from ufwi_ruleset.forward.match import objectsMatch, objectsOverlap
from ufwi_ruleset.forward.object import Object
from ufwi_ruleset.forward.rule.attribute import Identifier

class Rule(Object):
    id = Identifier()
    mandatory = Boolean(True)
    enabled = Boolean(True)

    # Name of valid attributes for match()
    MATCH_ATTRIBUTES = set()

    def __init__(self, rules, attr, loader_context=None):
        self.rules = rules
        self.ruleset = rules.ruleset   # used by ObjectSet
        Object.__init__(self, attr, loader_context)

    @classmethod
    def fromXML(cls, rules, attr, context, action):
        attr['id'] = (int(attr['id']) * 10) + context.ruleset_id
        rule_class = rules.RULE_CLASS
        rule = rule_class(rules, attr, context)
        if action:
            create = rules._createAction(rule)
            action.executeAndChain(create)
        else:
            rules._create(rule)
        return rule

    def isInput(self):
        return False

    def isOutput(self):
        return False

    def isForward(self):
        return False

    def checkRule(self, apply_rules, recursive=False):
        # Check if a referent is a genric object
        for ref in self.getReferents():
            if not ref.isGeneric(recursive):
                continue
            if self.mandatory:
                apply_rules.error(
                    tr("Mandatory rule %s uses an undefined generic object: %s"),
                    unicode(self), unicode(ref))
            else:
                apply_rules.warning(
                    tr("Ignore optional rule %s: physical object of %s missing"),
                    unicode(self), unicode(ref))
            return False

        address_types = self.getAddressTypes() - set((INTERFACE_ADDRESS,))
        if (address_types == set((IPV6_ADDRESS,))) \
        and (not self.ruleset.useIPv6()):
            # Ignore IPv6 rule: IPv6 is disabled
            return False
        return True

    def _removeTemplate(self, action, name):
        Object._removeTemplate(self, action, name)
        attr = self.getAttributes()
        attr['id'] = self.rules.createID()
        change_attr = self.rules.modifyObjectAction(self, attr)
        action.chain(change_attr)

    def match(self, rule, attributes):
        """
        If True if self matchs rule for the requested attributes.

        Example (www.google.fr is included in Internet):

         - rule A: LAN --HTTP--> Internet
         - rule B: LAN --HTTP--> www.google.fr

        A.match(B, ['sources']) -> True
        A.match(B, ['destinations']) -> True
        B.match(A, ['destinations']) -> False
        """
        return self._match(rule, attributes, objectsMatch)

    def overlaps(self, rule, attributes):
        """
        If True if self overlaps rule for the requested attributes.

        Example (www.google.fr is included in Internet):

         - rule A: LAN ---HTTP----> Internet
         - rule B: LAN --Any TCP--> www.google.fr

        A.overlaps(B, ['sources', 'protocols', 'destinations']) -> True

        whereas

        A.match(B, ['sources', 'protocols', 'destinations']) -> False
        B.match(A, ['sources', 'protocols', 'destinations']) -> False
        """
        return self._match(rule, attributes, objectsOverlap)

    def _match(self, rule, attributes, match_func):
        if not attributes:
            raise RulesetError(tr("Empty attribute list"))
        for attr in attributes:
            if attr not in self.MATCH_ATTRIBUTES:
                raise RulesetError(tr("Unknown rule attribute: %s"), attr)
            # TODO platform use flattenNetworkList
            objects_a = getattr(self, attr)
            objects_b = getattr(rule, attr)
            if not match_func(objects_a, objects_b):
                return False
        return True

    def getOrder(self):
        chain = self.rules.getAclChain(self)
        return chain.getOrder(self)

    # --- abstract methods ---

    @abstractmethod
    def createChainKey(self):
        pass

