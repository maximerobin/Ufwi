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

from __future__ import with_statement
from datetime import datetime
from errno import ENOENT
from os import umask
from os.path import basename

from ufwi_rpcd.backend import tr
from ufwi_rpcd.common.error import exceptionAsUnicode, reraise
from ufwi_rpcd.common.odict import odict
from ufwi_rpcd.common.xml_etree import etree, save as xml_save

from ufwi_conf.common.netcfg import NoMatch
from ufwi_ruleset.common.network import IPV4_ADDRESS, IPV6_ADDRESS

from ufwi_ruleset.forward.resource import (
    INTERNET_IPV4, INTERNET_IPV6, LOCAL_LINK_IPV6, LOCAL_MULTICAST_IPV6,
    Resources, InterfaceResource, NetworkResource, FirewallResource)
from ufwi_ruleset.forward.action import Action, ActionHandler, Update, Updates
from ufwi_ruleset.forward.action_stack import ActionStack
from ufwi_ruleset.forward.application import Applications
from ufwi_ruleset.forward.client import createLocalClient
from ufwi_ruleset.forward.config import LIBRARY_FILENAME
from ufwi_ruleset.forward.custom_rules import CustomRules
from ufwi_ruleset.forward.duration import Durations
from ufwi_ruleset.forward.error import RulesetError
from ufwi_ruleset.forward.fusion import Fusion
from ufwi_ruleset.forward.generic_links import GenericLinks
from ufwi_ruleset.forward.operating_system import OperatingSystems
from ufwi_ruleset.forward.parameters import NUFW_GATEWAY
from ufwi_ruleset.forward.periodicity import Periodicities
from ufwi_ruleset.forward.platform import Platforms
from ufwi_ruleset.forward.protocol import Protocols
from ufwi_ruleset.forward.rule.acl_rules import AclIPv4Rules, AclIPv6Rules
from ufwi_ruleset.forward.rule.nat_rules import NatRules
from ufwi_ruleset.forward.ruleset_loader import (RULESET_VERSION,
    LoadRulesetContext, rulesetFilename)
from ufwi_ruleset.forward.user_group import UserGroups

# None: unlimited number of undo actions
UNDO_MAX_SIZE = None

# Ruleset library name
LIBRARY_NAME = u"ufwi_ruleset"

class IncludeTemplate:
    def __init__(self, name, parent, identifier):
        self.name = name
        self.parent = parent
        self.identifier = identifier

    def _setParent(self, parent):
        self.parent = parent

    def exportXMLRPC(self):
        direct = not self.parent
        data = {
            'name': self.name,
            'identifier': self.identifier,
            'direct': direct}
        if self.parent:
            data['parent'] = self.parent
        return data

class Ruleset:
    """
    A ruleset contains resources, protocols and acls.
    Attributes:
     - filename: full path of the last saved version
     - name: filename without path and without ".xml" suffix, None if the
       ruleset is not yet saved on the disk
     - is_modified (bool): True if the ruleset is modified since the last
       save, always True if the ruleset is not saved yet
    """

    def __init__(self, component, logger, netcfg,
    read_only=False, client=None):
        # Define ruleset attributes
        if not client:
            self.client = createLocalClient()
        else:
            self.client = client
        self.name = None
        self.filename = None
        self.filetype = "ruleset"
        self.is_template = False
        self.read_only = read_only
        self.input_output_rules = component.input_output_rules
        self.format_version = RULESET_VERSION
        self.config = component.config

        # Create object libraries
        self.resources = Resources(self)
        self.protocols = Protocols(self)
        self.applications = Applications(self)
        self.periodicities = Periodicities(self)
        self.operating_systems = OperatingSystems(self)
        self.user_groups = UserGroups(self)
        self.durations = Durations(self)
        self.acls_ipv4 = AclIPv4Rules(self)
        self.acls_ipv6 = AclIPv6Rules(self)
        self.nats = NatRules(self)
        self.rules = {
            'acls-ipv4': self.acls_ipv4,
            'acls-ipv6': self.acls_ipv6,
            'nats': self.nats,
        }
        self.platforms = Platforms(self)

        self.custom_rules = CustomRules(self)
        self.include_templates = {}   # name => IncludeTemplate object
        # order is cosmetic
        self._libraries = odict((
            ('resources', self.resources),
            ('protocols', self.protocols),
            ('platforms', self.platforms),
            ('applications', self.applications),
            ('periodicities', self.periodicities),
            ('operating_systems', self.operating_systems),
            ('user_groups', self.user_groups),
            ('durations', self.durations),
            ('acls_ipv4', self.acls_ipv4),
            ('acls_ipv6', self.acls_ipv6),
            ('nats', self.nats),
        ))

        self.createBaseObjects(logger, netcfg)

        # Generic links, fusion and actions attributes
        self.generic_links = GenericLinks(self)
        self.generic_links.load()
        self.fusion = Fusion(self)
        self.actions = ActionStack(self, UNDO_MAX_SIZE)

    def load(self, logger, filetype, name, filename=None, content=None):
        self.name = name
        if filename:
            self.filename = filename
        else:
            self.filename = rulesetFilename(filetype, name)
        self.filetype = filetype
        self.is_template = (filetype == "template")

        loader_context = LoadRulesetContext(logger)
        # Load an existing ruleset/template
        self.loadFile(loader_context, self.filetype, self.name,
            editable=True, filename=self.filename, content=content,
            ruleset_id=0)
        self.updateFusion()
        return self.formatRuleset(loader_context)

    def create(self, logger, filetype, netcfg, base_template=None):
        self.name = None
        self.filename = None
        self.filetype = filetype
        self.is_template = (filetype == "template")

        loader_context = LoadRulesetContext(logger)
        if base_template:
            self.loadTemplate(loader_context, base_template, from_template=base_template)
        if self.filetype == "ruleset":
            self.createSystemNetworks(logger, netcfg)
            if not base_template:
                self.createBuiltinNetworks(logger, netcfg)
        self.updateFusion()
        return self.formatRuleset(loader_context)

    def createBaseObjects(self, logger, netcfg):
        loader_context = LoadRulesetContext(logger)
        # Load the standard library (protocols, periodicities, etc.),
        # and create the firewall object
        try:
            self.loadFile(loader_context, "library", u"ufwi_ruleset",
                # Use invalid identifier just to log with at a different log level
                ruleset_id=-1)
        except Exception, err:
            self.loadError(err, tr('the standard library'))
        firewall = FirewallResource(self.resources, netcfg)
        self.resources._create(firewall)

    def updateFusion(self, action=None, add_updates=False):
        self.fusion.replace(self.generic_links, action, add_updates)

    def _createNetworkIdentifier(self, logger, orig_identifier):
        identifier = self.resources.createIdentifier(orig_identifier)
        if identifier != orig_identifier:
            logger.error('Duplicate network identifier: replace "%s" by "%s".'
                % (orig_identifier, identifier))
        return identifier

    def _createNetwork(self, logger, action, interface_id, identifier, address):
        interface = self.resources[interface_id]
        network = interface.getNetworkByAddress(address)
        if network is not None:
            if network.id != identifier \
            and not network.id.startswith(identifier):
                identifier = self._createNetworkIdentifier(logger, identifier)
                logger.info('Network %s identifier changed: "%s" -> "%s"'
                            % (network.address, network.id, identifier))
                rename = interface.renameAction(network, identifier)
                if action:
                    action.executeAndChain(rename)
                else:
                    rename.apply()
            return

        identifier = self._createNetworkIdentifier(logger, identifier)
        attr = {'id': identifier, 'address': address, 'editable': True}
        network = NetworkResource(interface, attr)
        if action:
            create = interface._createAction(network)
            action.executeAndChain(create)
        else:
            interface._create(network)

    def createSystemNetworks(self, logger, netcfg, action=None):
        self._createSystemInterfaces(logger, netcfg, action)
        self._createSystemNetworks(logger, netcfg, action)

    def _createSystemInterfaces(self, logger, netcfg, action):
        for netcfg_interface in netcfg.iterInterfaces():
            identifier = unicode(netcfg_interface.fullName())
            interface_name = unicode(netcfg_interface.system_name)
            interface = self.resources.getInterfaceByName(interface_name)
            if interface is not None:
                if interface.id != identifier \
                and not interface.id.startswith(identifier):
                    identifier = self._createNetworkIdentifier(logger, identifier)
                    logger.info('Interface "%s" identifier changed: "%s"' % (interface.id, identifier))
                    rename = self.resources.renameAction(interface, identifier)
                    action.executeAndChain(rename)
                continue
            attr = {'id': identifier, 'name': interface_name, 'editable': True}
            interface = InterfaceResource(self.resources, attr)
            if action:
                create = self.resources._createAction(interface)
                action.executeAndChain(create)
            else:
                self.resources._create(interface)

    def _createSystemNetworks(self, logger, netcfg, action):
        for net in netcfg.iterNetworks():
            net_interface = netcfg.getInterfaceForNet(net)
            self._createNetwork(logger, action,
                unicode(net_interface.fullName()),
                unicode(net.label),
                net.net)

        for route in netcfg.iterRoutes():
            address = route.dst
            if address == INTERNET_IPV6:
                identifier = u"Internet IPv6"
            elif address == INTERNET_IPV4:
                identifier = u"Internet IPv4"
            else:
                identifier = unicode(address)
            route_interface = netcfg.getInterfaceForRoute(route)
            self._createNetwork(logger, action,
                unicode(route_interface.fullName()),
                identifier,
                address)

    def createBuiltinNetworks(self, logger, netcfg):
        # Create "Internet IPv4", "Internet IPv6",
        # "Local link IPv6" and "Local multicast IPv6" objects
        try:
            address, netcfg_interface = netcfg.getDefaultGateway(4)
        except NoMatch:
            logger.error("No default IPv4 gateway: don't create Internet objects")
            return
        interface_id = netcfg_interface.fullName()

        address_types = set()
        for interface in self.resources.itervalues():
            address_types |= interface.getAddressTypes()

        interface = self.resources[interface_id]
        networks = []
        if IPV4_ADDRESS in address_types:
            networks.append({'id': u'Internet IPv4', 'address': INTERNET_IPV4, 'editable': True})
        if IPV6_ADDRESS in address_types:
            networks.extend((
                {'id': u'Internet IPv6', 'address': INTERNET_IPV6, 'editable': True},
                {'id': u'Local link IPv6', 'address': LOCAL_LINK_IPV6, 'editable': True},
                {'id': u'Local multicast IPv6', 'address': LOCAL_MULTICAST_IPV6, 'editable': True},
            ))
        for attr in networks:
            network = interface.getNetworkByAddress(attr['address'])
            if network is not None:
                # System configuration already contains the network: skip it
                continue
            network = NetworkResource(interface, attr)
            interface._create(network)

    def getLibrary(self, name):
        try:
            return self._libraries[name]
        except KeyError:
            raise RulesetError(tr('Uknown library "%s"'), name)

    def getRuleList(self, rule_type):
        try:
            return self.rules[rule_type]
        except KeyError:
            raise RulesetError(tr("Unknown rule type: %s"), repr(rule_type))

    def loadError(self, err, when):
        message = u"[%s] %s" % (err.__class__.__name__, exceptionAsUnicode(err))
        if self.name:
            err = RulesetError(
                tr('Error while loading %s from the "%s" rule set: %s'),
                when, self.name, message)
        else:
            err = RulesetError(
                tr('Error on new rule set creation (while loading %s): %s'),
                when, message)
        reraise(err)

    def loadTemplate(self, loader_context, name,
    action=None, from_template=None):
        if from_template != name:
            parent = from_template
        else:
            parent = None

        if parent and (name in self.include_templates):
            template = self.include_templates[name]
            loader_context.logger.warning("Skip template %s: included twice.")

            updates = Updates(Update("ruleset", "update", -1))
            set_parent = Action(
                ActionHandler(updates, template._setParent, parent),
                ActionHandler(updates, template._setParent, template.parent))
            action.executeAndChain(set_parent)
            return

        template = self._createTemplate(name, parent)
        templates = (template,)
        if action:
            updates = Updates(Update("ruleset", "update", -1))
            add_template = Action(
                ActionHandler(updates, self._addTemplates, templates),
                ActionHandler(updates, self._removeTemplates, (template.name,)))
            action.executeAndChain(add_template)
        else:
            self._addTemplates(templates)

        was_template = self.is_template
        try:
            self.is_template = True
            self.loadFile(loader_context, "template", name,
                action=action, from_template=from_template,
                ruleset_id=template.identifier)
        finally:
            self.is_template = was_template

    def loadIncludes(self, context, xml_root, action):
        ruleset_context = context.ruleset_context

        # Load external files <include>
        has_include = False
        for node in xml_root.findall(u"include"):
            if 'template' in node.attrib:
                # Load a template
                has_include = True
                name = node.attrib['template']
                if context.from_template:
                    from_template = context.from_template
                else:
                    from_template = name
                try:
                    self.loadTemplate(ruleset_context, name,
                        action=action, from_template=from_template)
                except Exception, err:
                    self.loadError(err, tr('the template "%s"') % name)
            else:
                # Other: ignore unknown include
                continue
        if has_include:
            ruleset_context.logger.debug("Includes loaded, continue with the rule set")

    def loadFile(self, ruleset_context, filetype, name,
    editable=False, from_template=None, action=None, ruleset_id=0,
    filename=None, content=None):
        # Log the action
        logger = ruleset_context.logger
        text = "Load %s: %s" % (filetype, name)
        if ruleset_id == 0:
            logger.info(text)
        else:
            logger.debug(text)

        if not content:
            # Get the filename
            if not filename:
                if filetype == "library":
                    filename = LIBRARY_FILENAME
                else:
                    filename = rulesetFilename(filetype, name)

            # Parse the XML file
            try:
                with open(filename) as fp:
                    ruleset = etree.parse(fp).getroot()
            except IOError, err:
                if err.errno == ENOENT:
                    if filetype == 'template':
                        message = tr('The "%s" template does not exist. It has been deleted or renamed.')
                    else:
                        message = tr('The "%s" rule set does not exist. It has been deleted or renamed.')
                    raise RulesetError(message, name)
                else:
                    raise RulesetError(
                        tr('Unable to open file "%s" (%s): %s'),
                        basename(filename), filetype, exceptionAsUnicode(err))
        else:
            ruleset = etree.fromstring(content) #.getroot()

        # Create loader context
        version = ruleset.attrib.get('version', u'')
        if editable:
            self.format_version = version
        context = ruleset_context.createFileContext(filetype, name, version,
            editable, from_template, ruleset_id)

        # Load includes
        if filetype in ("ruleset", "template"):
            self.loadIncludes(context, ruleset, action)

        # Load objects
        for library, what in (
            (self.protocols, u"Protocols"),
            (self.applications, u"Applications"),
            (self.periodicities, u"Periodicities"),
            (self.durations, u"Durations"),
            (self.operating_systems, u"Operating systems"),
        ):
            try:
                library.importXML(ruleset, context, action)
            except Exception, err:
                self.loadError(err, what)

        if filetype in ("ruleset", "template"):
            libraries = [
                (self.resources, u"Networks"),
                (self.platforms, u"Platforms"),
                (self.user_groups, u"User groups"),
                (self.acls_ipv4, u"IPv4 ACL rules"),
            ]
            if context.version not in ("3.0m3", "3.0dev4", "3.0dev5"):
                libraries.append((self.acls_ipv6, u"IPv6 ACL rules"))
            libraries.append((self.nats, u"NAT rules"))
            for library, what in libraries:
                try:
                    library.importXML(ruleset, context, action)
                except Exception, err:
                    self.loadError(err, what)

        if filetype == "ruleset":
            self.custom_rules.importXML(ruleset, context)

    def save(self):
        if not self.filename:
            raise RulesetError(tr("A new rule set has no filename"))
        self.write(self.filename)

    def formatRuleset(self, loader_context=None):
        if self.client.mode != 'CLI':
            # GUIs
            data = {
                'rulesetAttributes': self.exportXMLRPC(),
                'undoState': self.undoState()}
            if loader_context:
                data['warnings'] = loader_context.warnings
            return data
        else:
            return None

    def saveAs(self, name):
        filename = rulesetFilename(self.filetype, name, check_existing=True)
        self.write(filename, name)
        return self.formatRuleset()

    def write(self, filename, save_as=None):
        if save_as:
            name = save_as
        else:
            name = self.name

        # Create the XML tree
        root = self.exportXML(name)

        umask(0077)
        xml_save(root, filename)

        if save_as:
            self.name = save_as
            self.filename = filename

        self.generic_links.write()

        if filename == self.filename:
            self.actions.setSavedState()

    def exportXML(self, name):
        now = unicode(datetime.now())
        now = now.split(".", 1)[0]
        attr = {
            'version': RULESET_VERSION,
            'name': name,
            'timestamp': now,
        }
        root = etree.Element("ruleset",  **attr)

        for template in self.include_templates.itervalues():
            if template.parent:
                continue
            etree.SubElement(root, "include", template=template.name)

        for library in self._libraries.itervalues():
            library.exportXML(root)
        if self.filetype == "ruleset":
            self.custom_rules.exportXML(root)
        return root

    def __repr__(self):
        if self.name:
            return '<Ruleset name=%r>' % self.name
        else:
            return '<Ruleset *new*>'

    def addAction(self, action, apply=True):
        if apply:
            action.apply()
        self.actions.add(action)
        return self.formatAction(action, True)

    def formatAction(self, action, apply):
        mode = self.client.mode
        if mode == 'CLI':
            # mode CLI: return None
            return None
        if apply:
            updates = action.createApplyTuple()
        else:
            updates = action.createUnapplyTuple()
        if mode != 'GUI2':
            # mode GUI: return the updates
            return updates
        # mode GUI2: return updates and undo state
        return {
            'updates': updates,
            'undoState': self.undoState(),
        }

    def useIPv6(self):
        return self.config['global']['use_ipv6']

    def useNuFW(self):
        return (self.config['global']['firewall_type'] == NUFW_GATEWAY)

    def isModified(self):
        return (not self.name) or (not self.actions.isSavedState())

    def restoreReferences(self):
        for library in (self.resources, self.protocols, self.applications,
        self.periodicities, self.operating_systems, self.user_groups,
        self.durations):
            for item in library.itervalues():
                item.registerReferences()
        for rules in self.rules.itervalues():
            for rule in rules:
                rule.registerReferences()

    def getTemplate(self, identifier):
        for template in self.include_templates.itervalues():
            if template.identifier == identifier:
                return template
        raise RulesetError(tr("There is not template #%s"), identifier)

    def exportXMLRPC(self):
        templates = [template.exportXMLRPC()
            for template in self.include_templates.itervalues()]
        attr = {
            'is_template': self.is_template,
            'filetype': self.filetype,
            'templates': templates,
            'format_version': self.format_version,
            'read_only': self.read_only,
            'input_output_rules': self.input_output_rules,
        }
        if self.name:
            attr['name'] = self.name
        return attr

    def _setTemplate(self):
        self.is_template = True

    def _unsetTemplate(self):
        self.is_template = True

    def addTemplate(self, logger, name):
        loader_context = LoadRulesetContext(logger)
        template = self._createTemplate(name, None)

        # Set template mode
        updates = Updates(Update("ruleset", "update", -1))
        action = Action(
            ActionHandler(updates, self._setTemplate),
            ActionHandler(updates, self._unsetTemplate))
        action.apply()

        try:
            # Register the template
            names = (template.name,)
            templates = (template,)
            add_template = Action(
                ActionHandler(updates, self._addTemplates, templates),
                ActionHandler(updates, self._removeTemplates, names))
            action.executeAndChain(add_template)

            # Load the template objects (create actions)
            self.loadFile(loader_context, "template", name, action=action,
                from_template=name, ruleset_id=template.identifier)

            # Unset template flag
            unset = Action(
                ActionHandler(updates, self._unsetTemplate),
                ActionHandler(updates, self._setTemplate))
            action.executeAndChain(unset)
        except:
            # Rollback
            action.unapply()
            raise
        return self.addAction(action, apply=False)

    def _createTemplate(self, name, parent):
        if (name in self.include_templates) \
        or (self.is_template and (self.name == name)):
            raise RulesetError(
                tr('The "%s" template can not be included twice'),
                name)
        identifier = 1 + len(self.include_templates)
        if 9 < identifier:
            raise RulesetError(tr("A rule set cannot comprise more than 9 templates!"))
        return IncludeTemplate(name, parent, identifier)

    def _removeTemplates(self, names):
        for name in names:
            del self.include_templates[name]

    def _addTemplates(self, templates):
        for template in templates:
            self.include_templates[template.name] = template

    def removeTemplate(self, name):
        template = self.include_templates[name]
        if template.parent:
            raise RulesetError(
                tr('It is not possible to delete the "%s" template, included in the "%s" template'),
                name, template.parent)
        templates = [template]
        for template in self.include_templates.itervalues():
            if template.parent != name:
                continue
            templates.append(template)
        names = [template.name for template in templates]

        updates = Updates(Update("ruleset", "update", -1))
        action = Action(
            ActionHandler(updates, self._removeTemplates, names),
            ActionHandler(updates, self._addTemplates, templates))
        action.apply()

        try:
            for library in self._libraries.itervalues():
                library.removeTemplate(action, name)
        except:
            # Rollback
            action.unapply()
            raise
        return self.addAction(action, apply=False)

    def __setstate__(self, state):
        """
        Restore a ruleset from a pickle file: restore the references.
        """
        self.__dict__ = state
        self.restoreReferences()

    def undoState(self):
        return (self.isModified(), self.actions.canUndo(), self.actions.canRedo())

    def undoLast(self):
        action = self.actions.undoLast()
        return self.formatAction(action, False)

    def redoLast(self):
        action = self.actions.redoLast()
        return self.formatAction(action, True)

    def ufwi_confSync(self, logger, netcfg):
        action = Action.createEmpty()
        self.createSystemNetworks(logger, netcfg, action)
        return self.addAction(action, False)

    def setCustomRules(self, rules):
        if self.filetype != "ruleset":
            raise RulesetError(tr('Custom rules are not allowed in templates.'))
        self.custom_rules.setRules(rules)

