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
from ufwi_rpcd.common.xml_etree import etree

from ufwi_ruleset.forward.error import RulesetError
from ufwi_ruleset.forward.action import Action, ActionHandler, Update, Updates
from ufwi_ruleset.forward.rule.chain import InputChain, OutputChain, ForwardChain
from ufwi_ruleset.forward.object_set import ObjectSet

class Rules(ObjectSet):
    RULE_CLASS = None
    UPDATE_DOMAIN = None
    UPDATE_CHAIN_DOMAIN = None

    def __init__(self, ruleset, xml_tag):
        ObjectSet.__init__(self, ruleset)
        self.next_id = 1
        self.xml_tag = xml_tag

        # acl identifier (int) => Acl object
        self.acls = {}

        # ("eth0", "eth1") or "INPUT" => InputChain, OutputChain or ForwardChain
        self.chains = {}

    def createID(self):
        identifier = self.next_id * 10
        self.next_id += 1
        return identifier

    def _add(self, acls):
        for acl, position in acls:
            if acl.id in self.acls:
                raise RulesetError(tr("Duplicate rule identifier: %s!"), acl.id)
            self.acls[acl.id] = acl

            self.next_id = max(self.next_id, acl.id // 10 + 1)

            chain = self.getAclChain(acl, create=True)
            if position is not None:
                chain.insert(position, acl)
            else:
                chain.append(acl)
            acl.registerReferences()
        return acls

    def _deleteChain(self, chain, rule):
        chain.remove(rule)
        if not chain:
            del self.chains[chain.key]

    def _delete(self, acls):
        for acl in acls:
            acl.unregisterReferences()
            del self.acls[acl.id]
            chain = self.getAclChain(acl, create=False)
            self._deleteChain(chain, acl)

    def create(self, attr):
        attr['id'] = self.createID()
        position = attr.pop('position', None)
        rule = self.RULE_CLASS(self, attr)
        action = self._createAction(rule, position)
        updates = self.ruleset.addAction(action)
        return updates

    def _create(self, rule):
        add = ((rule, None),)
        self._add(add)

    def checkEditable(self, *rules):
        for rule in rules:
            if rule.editable:
                continue
            raise RulesetError(tr("%s is not editable!"), unicode(rule))

    def _replace(self, rule, attr, order):
        old_chain = self.getAclChain(rule)
        self._setattr(rule, attr)
        new_chain = self.getAclChain(rule, create=True)
        if old_chain != new_chain:
            self._deleteChain(old_chain, rule)
            if order is not None:
                new_chain.insert(order, rule)
            else:
                new_chain.append(rule)

    def _rename(self, object, old_id, new_id):
        del self.acls[old_id]
        self.acls[new_id] = object

    def modifyObjectAction(self, acl, new_attr):
        self.checkEditable(acl)

        old_attr = acl.getAttributes()
        if 'id' not in new_attr:
            new_attr['id'] = old_attr['id']
        tmp_acl = self.RULE_CLASS(self, new_attr)

        domain = self.UPDATE_DOMAIN
        chain_domain = self.UPDATE_CHAIN_DOMAIN

        old_chain1 = self.getAclChain(acl)
        old_chain2 = self.getAclChain(tmp_acl)
        if old_chain1 == old_chain2:
            if acl.id == tmp_acl.id:
                apply_updates = Updates(Update(domain, "update", acl.id))
                unapply_updates = apply_updates
            else:
                apply_updates = Updates(
                    Update(domain, "delete", acl.id),
                    Update(domain, "create", tmp_acl.id))
                unapply_updates = Updates(
                    Update(domain, "delete", tmp_acl.id),
                    Update(domain, "create", acl.id))
            referents = set(acl.getReferents()) ^ set(tmp_acl.getReferents())
            action = Action(
                ActionHandler(apply_updates, self._setattr, acl, new_attr),
                ActionHandler(unapply_updates, self._setattr, acl, old_attr))
            action.apply()
            self._updateObjects(action, referents)
        else:
            old_order = old_chain1.getOrder(acl)
            if 1 < len(old_chain1):
                apply_update1 = Update(chain_domain, "update",
                    old_chain1.createUpdateKey())
                unapply_update1 = Update(chain_domain, "update",
                    old_chain1.createUpdateKey(acl))
            else:
                apply_update1 = Update(chain_domain, "delete",
                    old_chain1.createUpdateKey())
                unapply_update1 = Update(chain_domain, "create",
                    old_chain1.createUpdateKey(acl))

            if old_chain2 is None:
                old_chain2 = self.getAclChain(tmp_acl, create=True)
                apply_update2 = Update(chain_domain, "create",
                    old_chain2.createUpdateKey(tmp_acl))
                unapply_update2 = Update(chain_domain, "delete",
                    old_chain2.createUpdateKey())
            else:
                apply_update2 = Update(chain_domain, "update",
                    old_chain2.createUpdateKey(tmp_acl))
                unapply_update2 = Update(chain_domain, "update",
                    old_chain2.createUpdateKey())

            apply_updates = Updates(apply_update1, apply_update2)
            unapply_updates = Updates(unapply_update2, unapply_update1)
            action = Action(
                ActionHandler(apply_updates, self._replace,
                    acl, new_attr, None),
                ActionHandler(unapply_updates, self._replace,
                    acl, old_attr, old_order))
            action.apply()

        old_referents = set(acl.getReferents())
        new_referents = set(tmp_acl.getReferents())
        for object in (old_referents ^ new_referents):
            # update references
            update = object.createUpdate()
            action.addApplyUpdate(update)
            action.addUnapplyUpdate(update)
        return action

    def _createAction(self, rule, position=None):
        domain = self.UPDATE_DOMAIN
        apply_updates = Updates(Update(domain, "create", rule.id))
        unapply_updates = Updates(Update(domain, "delete", rule.id))
        add = ((rule, position),)
        action = Action(
            ActionHandler(apply_updates, self._add, add),
            ActionHandler(unapply_updates, self._delete, (rule,)))
        self._updateObjects(action, rule.getReferents())
        return action

    def clone(self, acl_id):
        old_acl = self.acls[acl_id]
        attr = old_acl.getAttributes()
        attr['id'] = self.createID()
        attr['editable'] =  True
        rule = self.RULE_CLASS(self, attr)
        action = self._createAction(rule)
        updates = self.ruleset.addAction(action)
        return updates

    def getAcls(self, identifiers):
        return [ self.acls[acl_id] for acl_id in identifiers ]

    def delete(self, identifiers):
        acls = self.getAcls(identifiers)
        self.checkEditable(*acls)
        domain = self.UPDATE_DOMAIN
        apply_updates = Updates(Update(domain, "delete", *identifiers))
        unapply_updates = Updates(Update(domain, "create", *identifiers))
        referents = set(acls[0].getReferents())
        for acl in acls[1:]:
            referents |= set(acl.getReferents())
        add = [(acl, acl.getOrder()) for acl in acls]
        action = Action(
            ActionHandler(apply_updates, self._delete, acls),
            ActionHandler(unapply_updates, self._add, add))
        self._updateObjects(action, referents)
        return self.ruleset.addAction(action)

    def moveAt(self, rule, new_order):
        chain = self.getAclChain(rule)
        old_order = chain.getOrder(rule)

        update = Update(self.UPDATE_CHAIN_DOMAIN, "update", chain.createUpdateKey(rule))
        action = Action(
            ActionHandler(update, chain.moveAcl, rule, new_order, self.checkEditable),
            ActionHandler(update, chain.moveAcl, rule, old_order, self.checkEditable))
        return self.ruleset.addAction(action)

    def getAclChain(self, acl, create=False):
        key = acl.createChainKey()
        if create:
            if key not in self.chains:
                if acl.isInput():
                    self.chains[key] = InputChain()
                elif acl.isOutput():
                    self.chains[key] = OutputChain()
                else:
                    self.chains[key] = ForwardChain(acl.input, acl.output)
            return self.chains[key]
        else:
            return self.chains.get(key)

    def importXMLRules(self, rules, context, action):
        # Reset the identifier generator
        old_next_id = self.next_id
        if context.version not in ("3.0m3", "3.0dev4"):
            self.next_id = int(rules.attrib['next_id'])
        else:
            self.next_id = 1

        # Load the rules
        cls = self.RULE_CLASS
        for node in rules.findall(cls.XML_TAG):
            cls.importXML(self, node, context, action)

        # Restore the identifier generator if loading an include
        if context.ruleset_id != 0:
            self.next_id = old_next_id

    def importXML(self, xml_root, context, action):
        if self.xml_tag == "acls_ipv4" \
        and context.version in ("3.0m3", "3.0dev4", "3.0dev5"):
            # Old format use <acls> instead of <acls_ipv4>
            xml_tag = "acls"
        else:
            xml_tag = self.xml_tag
        rules = xml_root.find(xml_tag)
        if rules is None:
            return
        self.importXMLRules(rules, context, action)

    def exportXMLRules(self, parent):
        chains = self.chains.values()
        chains.sort(key=lambda chain: chain.key)
        empty = True
        for chain in chains:
            empty &= chain.exportXML(parent)
        return empty

    def exportXML(self, root):
        if not self.chains:
            return
        parent = etree.SubElement(root, self.xml_tag,
            next_id=unicode(self.next_id))
        empty = self.exportXMLRules(parent)
        if empty:
            root.remove(parent)

    def __getitem__(self, aclid):
        return self.acls[aclid]

    def __contains__(self, identifier):
        return identifier in self.acls

    def __iter__(self):
        for chain in self.iterchains():
            for rule in chain:
                yield rule

    def getChain(self, key):
        return self.chains[key]

    def iterchains(self):
        return self.chains.itervalues()

    def _sortChainKey(self, item):
        chain_key, rules = item
        order = 0
        if isinstance(chain_key, tuple):
            interfaces = self.ruleset.resources
            input_id, output_id = chain_key
            input = interfaces[input_id]
            output = interfaces[output_id]
            if input.isGeneric():
                order -= 1
            if output.isGeneric():
                order -= 1
        return (order, chain_key)

    def exportXMLRPC(self, fusion):
        interfaces = self.ruleset.resources
        xmlrpc = []
        xmlrpc_dict = {}
        chains = self.chains.items()
        chains.sort(key=self._sortChainKey)
        for chain_key, chain in chains:
            if fusion and isinstance(chain_key, tuple):
                input_id, output_id = chain_key
                input = interfaces[input_id]
                output = interfaces[output_id]
                chain_key = (input.getID(fusion), output.getID(fusion))
            chain_list = chain.exportXMLRPC(fusion)
            if chain_key in xmlrpc_dict:
                xmlrpc_dict[chain_key].extend(chain_list)
            else:
                xmlrpc.append((chain_key, chain_list))
                xmlrpc_dict[chain_key] = chain_list
        return xmlrpc

    def onInterfaceRename(self, interface, old_id):
        for chain in self.chains.values():
            old_key = chain.key
            new_key = chain.updateKey()
            if old_key == new_key:
                continue
            del self.chains[old_key]
            self.chains[new_key] = chain

