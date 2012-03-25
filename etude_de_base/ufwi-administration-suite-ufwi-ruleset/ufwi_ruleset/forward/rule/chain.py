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
from ufwi_ruleset.forward.error import RulesetError

class Chain:
    def __init__(self, key):
        self.key = key    # (u"eth0", u"eth2") or u"INPUT"
        self.acls = []

    def updateKey(self):
        return self.key

    def append(self, new_acl):
        ruleset_id = new_acl.id % 10
        for index, acl in enumerate(self.acls):
            if ruleset_id > (acl.id % 10):
                self.acls.insert(index, new_acl)
                return
        self.acls.append(new_acl)

    def insert(self, order, acl):
        self.acls.insert(order, acl)

    def remove(self, acl):
        self.acls.remove(acl)

    def moveAcl(self, acl, new_order, check_editable):
        # Compute rules order
        rules  = self.acls
        old_order = self.getOrder(acl)
        length = len(rules)

        # Consistency checks
        if not (0 <= new_order < length):
            if new_order < old_order:
                format = tr("Unable to move up the %s: the rule is already the first of the %s chain.")
            else:
                format = tr("Unable to move down the %s: the rule is already the last of the %s chain.")
            raise RulesetError(
                format,
                unicode(acl), unicode(self))

        if old_order < new_order:
            first = old_order
            last = new_order
        else:
            first = new_order
            last = old_order

        for order in xrange(first, last+1):
            print("check", order)
            check_editable(rules[order])

        # Move the rule
        rule = rules.pop(old_order)
        rules.insert(new_order, rule)

    def getOrder(self, acl):
        return self.acls.index(acl)

    def clone(self):
        bichain = self.__class__(self.key)
        bichain.acls = list(self.acls)
        return bichain

    def replaceAcl(self, old_acl, new_acl):
        order = self.getOrder(old_acl)
        self.acls[order] = new_acl

    def __iter__(self):
        return iter(self.acls)

    def createUpdateKey(self, acl=None):
        if acl:
            return (self.key, acl.id)
        else:
            return (self.key, -1)

    def exportXMLRPC(self, fusion):
        return [acl.exportXMLRPC(fusion) for acl in self.acls]

    def exportXML(self, parent):
        empty = True
        for rule in self:
            if not rule.editable:
                continue
            if rule.exportXML(parent) is not None:
                empty = False
        return empty

    def __repr__(self):
        return "<%s %s (%s ACLs)>" % (
            self.__class__.__name__, str(self), len(self.acls))

    def __len__(self):
        return len(self.acls)

    def __str__(self):
        return unicode(self).encode("ASCII", "backslashreplace")

    def __unicode__(self):
        return self.key

class InputChain(Chain):
    def __init__(self):
        Chain.__init__(self, u"INPUT")

    def clone(self):
        bichain = self.__class__()
        bichain.acls = list(self.acls)
        return bichain

class OutputChain(Chain):
    def __init__(self):
        Chain.__init__(self, u"OUTPUT")

    def clone(self):
        bichain = self.__class__()
        bichain.acls = list(self.acls)
        return bichain

class ForwardChain(Chain):
    def __init__(self, input, output):
        key = (input.id, output.id)
        Chain.__init__(self, key)
        self.input = input
        self.output = output

    def updateKey(self):
        self.key = (self.input.id, self.output.id)
        return self.key

    def clone(self):
        bichain = ForwardChain(self.input, self.output)
        bichain.acls = list(self.acls)
        return bichain

    def __unicode__(self):
        # U+2192: RIGHTWARDS ARROW
        return u"%s\u2192%s" % (self.input.id,  self.output.id)

