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
from os import umask
from os.path import exists

from ufwi_rpcd.common.xml_etree import etree, save
from ufwi_rpcd.common.transaction import Transaction
from ufwi_rpcd.common.logger import LoggerChild
from ufwi_rpcd.common.tools import abstractmethod

from ufwi_rpcd.backend.error import exceptionAsUnicode
from ufwi_rpcd.backend import tr

from ufwi_ruleset.forward.error import RulesetError
from ufwi_ruleset.forward.config import GENERIC_LINKS_XML
from ufwi_ruleset.forward.object import checkIdentifier
from ufwi_ruleset.forward.action import Action, ActionHandler, Updates, Update
from ufwi_ruleset.forward.user_group import getUserGroupNumber
from ufwi_ruleset.forward.resource import (
    InterfaceResource, NetworkResource, HostResource)
from ufwi_ruleset.forward.resource.tools import parseIPAddress
from ufwi_ruleset.forward.resource.network import checkHost
from ufwi_ruleset.forward.file import File, unlinkQuiet

FORMAT_VERSION = "3.0dev4"

class WriteGenericLinks(Transaction, LoggerChild):
    def __init__(self, links, logger):
        LoggerChild.__init__(self, logger)
        self.filename = GENERIC_LINKS_XML
        self.links = links
        self.old = File(self.filename + ".old", False)

    def prepare(self):
        filename = self.filename + ".new"
        generic_links = BaseGenericLinks(filename)
        generic_links.setLinks(self.links)
        generic_links.write()
        self.new = File(filename, True)

    def save(self):
        umask(0077)
        self.old.copyFrom(self.filename)

    def apply(self):
        self.error("Write new generic links")
        self.new.renameTo(self.filename)

    def rollback(self):
        if self.old.exist:
            self.old.renameTo(self.filename)
        else:
            unlinkQuiet(self.filename)

    def cleanup(self):
        self.old.unlink(quiet=True)
        self.new.unlink(quiet=True)

class Links(dict):
    def __init__(self, key, links):
        self.key = key
        for generic, physical in links.iteritems():
            self.addLink(generic, physical)

    def addLink(self, generic, physical):
        generic = unicode(generic)
        checkIdentifier(generic)
        physical = unicode(physical).strip()
        if physical:
            physical = self.createPhysical(physical)
        else:
            physical = None
        self[generic] = physical

    def setLinks(self, data):
        self.clear()
        for generic, physical in data.iteritems():
            self.addLink(generic, physical)

    def importXML(self, root):
        parent = root.find(self.key)
        if parent is None:
            return
        self.clear()
        for node in parent.findall(u'link'):
            generic = node.attrib['generic']
            physical = node.attrib['physical']
            self.addLink(generic, physical)

    def exportXML(self, root):
        items = self.items()
        if not items:
            return None
        items.sort(key=lambda(generic, physical): generic)

        node = etree.SubElement(root, self.key)
        for generic, physical in items:
            if physical is None:
                continue
            physical = unicode(physical)
            etree.SubElement(node, "link", generic=generic, physical=physical)
        return node

    def exportXMLRPC(self):
        xmlrpc = {}
        for generic, physical in self.iteritems():
            if physical is not None:
                physical = unicode(physical)
            else:
                physical = u''
            xmlrpc[generic] = physical
        return xmlrpc

    def getMissingLinks(self):
        return [generic
            for generic, physical in self.iteritems()
            if physical is None]

    @abstractmethod
    def createPhysical(self, physical):
        pass

class InterfaceLinks(Links):
    def createPhysical(self, name):
        checkIdentifier(name)
        return name

class NetworkLinks(Links):
    def createPhysical(self, text):
        ip = parseIPAddress(text)
        ip.NoPrefixForSingleIp = False
        return ip

class HostLinks(Links):
    def createPhysical(self, address):
        address = parseIPAddress(address)
        checkHost(address)
        return address

class UserGroupLinks(Links):
    def createPhysical(self, group):
        try:
            # group number (int)
            return getUserGroupNumber(group)
        except RulesetError:
            # group name (unicode)
            return unicode(group).strip()

class BaseGenericLinks(dict):
    """
    Generic links not linked to a ruleset.
    """
    def __init__(self, filename):
        self.filename = filename
        self.setLinks({})

    def createLinks(self, data):
        links = {}
        links["interfaces"] = InterfaceLinks("interfaces",
            data.pop("interfaces", {}))
        links["networks"] = NetworkLinks("networks",
            data.pop("networks", {}))
        links["hosts"] = HostLinks("hosts",
            data.pop("hosts", {}))
        links["user_groups"] = UserGroupLinks("user_groups",
            data.pop("user_groups", {}))
        keys = data.keys()
        if keys:
            raise RulesetError(
                tr("Unknown generic link keys: %s"),
                u', '.join(keys))
        return links

    def write(self):
        xml = etree.Element("generic_links", version=FORMAT_VERSION)
        for links in self.itervalues():
            links.exportXML(xml)
        umask(0077)
        save(xml, self.filename)

    def setLinks(self, links):
        links = self.createLinks(links)
        self._setLinks(links)

    def _setLinks(self, links):
        self.clear()
        self.update(links)

    def _create(self, key, object):
        if not object.isGeneric():
            return
        identifier = object.id
        if identifier in self[key]:
            return
        self[key][identifier] = None

class GenericLinks(BaseGenericLinks):
    """
    Generic links used by the ruleset.
    """
    def __init__(self, ruleset):
        self.ruleset = ruleset
        BaseGenericLinks.__init__(self, GENERIC_LINKS_XML)

    def setLinksAction(self, data):
        old_links = dict(self)
        new_links = self.createLinks(data)
        updates = Updates(Update("generic-links", "update", -1))
        action = Action(
            ActionHandler(updates, self._setLinksRuleset, new_links),
            ActionHandler(updates, self._setLinksRuleset, old_links))
        action.apply()
        self.ruleset.fusion.replace(self, action)
        return self.ruleset.addAction(action, apply=False)

    def _setLinksRuleset(self, links):
        self._setLinks(links)

    def createNew(self):
        for user_group in self.ruleset.user_groups.itervalues():
            self._create('user_groups', user_group)
        for network in self.ruleset.resources.itervalues():
            if isinstance(network, InterfaceResource):
                key = 'interfaces'
            elif isinstance(network, NetworkResource):
                key = 'networks'
            elif isinstance(network, HostResource):
                key = 'hosts'
            else:
                continue
            self._create(key, network)

    def load(self):
        if not exists(self.filename):
            return
        try:
            with open(self.filename) as fp:
                xml = etree.parse(fp).getroot()
        except IOError, err:
            raise RulesetError(
                tr('Unable to open the generic links file: %s'),
                exceptionAsUnicode(err))
        version = xml.attrib['version']
        if version != FORMAT_VERSION:
            raise RulesetError(
                tr('Unknown generic links format version: "%s"'),
                version)
        for links in self.itervalues():
            links.importXML(xml)

    def getMissingLinks(self):
        self.createNew()
        missings = {}
        for key, links in self.iteritems():
            missing = links.getMissingLinks()
            if not missing:
                continue
            missings[key] = missing
        return missings

    def exportXMLRPC(self):
        self.createNew()
        xmlrpc = {}
        for key, links in self.iteritems():
            xmlrpc[key] = links.exportXMLRPC()
        return xmlrpc

    def removeTemplateAction(self, action, template_name, key, object, error_format):
        links = self[key]
        try:
            physical = links[object.id]
        except KeyError:
            raise RulesetError(
                error_format,
                template_name, object.formatID())
        update = object.createUpdate()
        new_action = Action(
            ActionHandler(update, object.setPhysical, physical),
            ActionHandler(update, object.setGeneric))
        action.executeAndChain(new_action)

