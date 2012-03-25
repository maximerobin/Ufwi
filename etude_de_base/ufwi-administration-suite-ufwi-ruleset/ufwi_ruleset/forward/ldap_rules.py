"""
Copyright (C) 2009-2011 EdenWall Technologies

Written by Victor Stinner <vstinner AT edenwall.com>
Modified by Pierre-Louis Bonicoli <bonicoli@edenwall.com>

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
from ldap import initialize, SCOPE_SUBTREE, error as ldap_error
from ldap.modlist import addModlist

from ufwi_rpcd.common.tools import toUnicode
from ufwi_rpcd.common.transaction import Transaction
from ufwi_rpcd.common.logger import LoggerChild

from ufwi_rpcd.backend import tr
from ufwi_rpcd.backend.logger import Logger, ContextLoggerChild

from ufwi_ruleset.common.network import IPV6_ADDRESS
from ufwi_ruleset.common.rule import DECISIONS

from ufwi_ruleset.forward.protocol import IP_PROTOCOL
from ufwi_ruleset.forward.error import RulesetError
from ufwi_ruleset.forward.port_interval import PORT_MIN, PORT_MAX
from ufwi_ruleset.forward.flatten import flattenObject, flattenObjectList, \
    flattenNetworkList, zipallObjects
from ufwi_ruleset.forward.resource import (
    InterfaceResource, NetworkResource, HostnameResource, HostResource,
    INTERNET_IPV4, INTERNET_IPV6)
from ufwi_ruleset.forward.instanciation import TemplateInstanciation
from ufwi_ruleset.forward.apply_rules_result import ApplyRulesResult, filterRules

ACL_FLAGS_ASYNC = (1 << 0)
ACL_FLAGS_NOLOG = (1 << 1)
ACL_FLAGS_SYNC = (1 << 2)
ACL_FLAGS_STRICT = (1 << 3)

class ApplyLdapRules(Transaction, LoggerChild):
    def __init__(self, logger, ldap_config, ldap_rules):
        self.old_rules = []
        LoggerChild.__init__(self, logger)
        self.rules = ldap_rules
        self.ldap_config = ldap_config

    def prepare(self):
        self.info("Load LDAP rules")
        self.ldap = LdapConnection(self.getLogger(), self.ldap_config)

    def save(self):
        self.warning("Save the current LDAP rules")
        try:
            for cn, attr in self.ldap.searchRules():
                self.old_rules.append((cn, attr))
        except ldap_error, err:
            self.ldap.raiseError(err)

    def apply(self):
        self.error("Apply the new LDAP rules")
        try:
            self.ldap.applyRules(self.rules)
        except ldap_error, err:
            self.ldap.raiseError(err)

    def rollback(self):
        self.error("Restore the %s old LDAP rules" % len(self.old_rules))
        try:
            self.ldap.applyRules(self.old_rules)
        except ldap_error, err:
            self.ldap.raiseError(err)

class WriteLdapRules(LoggerChild):
    def __init__(self, logger, ldap_config):
        LoggerChild.__init__(self, logger)
        self.basedn = ldap_config['basedn']

    def createRules(self, acls):
        rules = []
        acl_index = 0
        for acl in acls:
            if (not acl.isForward()) or (not acl.user_groups):
                continue
            if acl.address_type == IPV6_ADDRESS:
                ip_version = 'ipv6'
            else:
                ip_version = 'ipv4'
            acl_index += 1
            for rule_index, attr in enumerate(self.aclRules(acl, acl_index)):
                # generate an unique CN
                attr['cn'] = u'%s_acl%s_rule%s' % (ip_version, acl.id, rule_index + 1)
                dn = 'cn=%s,%s' % (attr['cn'], self.basedn)
                self.createRule(rules, dn, attr)
        return rules

    def addressList(self, networks, address_type):
        for network in flattenNetworkList(networks):
            # no address: interface network
            if isinstance(network, InterfaceResource):
                if address_type == IPV6_ADDRESS:
                    yield INTERNET_IPV6
                else:
                    yield INTERNET_IPV4
            else:
                assert isinstance(network, (NetworkResource, HostResource, HostnameResource))
                addresses = list(network.getAddresses())
                addresses.sort()
                for address in addresses:
                    yield address

    def aclRules(self, acl, acl_index):

        flags = 0
        if not acl.log:
            flags |= ACL_FLAGS_NOLOG
# TODO:       if acl.transparent_proxy:
# TODO:           flags |= ACL_FLAGS_SYNC | ACL_FLAGS_STRICT
        decision = DECISIONS[acl.decision]
        common_attr = {
            'AclFlags': flags,
            'Decision': decision,
            'objectClass': (u'top', u'NuAccessControlList'),
            'AclWeight': acl_index,
        }
        if not acl.input.name.endswith('+'):
            common_attr['InDev'] = acl.input.name
        if not acl.output.name.endswith('+'):
            common_attr['OutDev'] = acl.output.name
        common_attr['description'] = acl.logPrefix(ldap=True)
        # TODO: PhysInDev PhysOutDev

        timeranges = set(acl.durations)
        timeranges.update(acl.periodicities)

#        if acl.source_platforms:
#            destinations = self.addressList(acl.destinations, acl.address_type)
#            for destination in destinations:
#                for platform in acl.source_platforms:
#                    for item in platform.items:
#                        sources = self.addressList(flattenObject(item.network), acl.address_type)
#                        protocols = flattenObject(item.protocol)
#                        for rule in self.aclRule(acl, common_attr, sources, [destination], protocols, timeranges):
#                            yield rule
#        elif acl.destination_platforms:
#            sources = self.addressList(acl.sources, acl.address_type)
#            for source in sources:
#                for platform in acl.destination_platforms:
#                    for item in platform.items:
#                        destinations = self.addressList(flattenObject(item.network), acl.address_type)
#                        protocols = flattenObject(item.protocol)
#                        for rule in self.aclRule(acl, common_attr, [source], destinations, protocols, timeranges):
#                            yield rule

        if not acl.source_platforms and not acl.destination_platforms:
            # Create source and destination addresses

            protocols = list(flattenObjectList(acl.protocols))
            protocols.sort(key=lambda protocol: protocol.sortKey())

            for rule in self.aclRule(acl, common_attr, acl.sources, acl.destinations, protocols, timeranges):
                yield rule

        else:
            if acl.source_platforms:
                platforms = acl.source_platforms
                networks = acl.destinations
            else:
                platforms = acl.destination_platforms
                networks = acl.sources

            for network in networks:
                for platform in platforms:
                    for item in platform.items:
                        platform_networks = flattenObject(item.network)
                        protocols = flattenObject(item.protocol)
                        if acl.source_platforms:
                            for rule in self.aclRule(acl, common_attr, platform_networks, [network], protocols, timeranges):
                                yield rule
                        else:
                            for rule in self.aclRule(acl, common_attr, [network], platform_networks, protocols, timeranges):
                                yield rule

    def aclRule(self, acl, common_attr, sources, destinations, protocols, timeranges):

        sources = self.addressList(sources, acl.address_type)
        destinations = self.addressList(destinations, acl.address_type)

        for saddr, daddr, protocol, user_group, application, operating_system, timerange\
        in zipallObjects(sources, destinations, protocols, acl.user_groups,
        acl.applications, acl.operating_systems, timeranges):

            if protocol.layer4 not in (u'tcp', u'udp'):
                raise RulesetError(tr('The protocol "%s" of the %s cannot be identified.'),
                    protocol.id, unicode(acl))
            layer4 = IP_PROTOCOL[protocol.layer4]
            attr = {
                'SrcIPStart': saddr.int(),
                'SrcIPEnd': saddr.broadcast().int(),
                'DstIPStart': daddr.int(),
                'DstIPEnd': daddr.broadcast().int(),
                'Proto': layer4,
                'AuthQuality': acl.auth_quality,
            }
            if user_group.group is not None:
                attr['Group'] = user_group.group
            if user_group.name:
                attr['GroupName'] = user_group.name

            sport = protocol.sport
            if sport:
                attr['SrcPortStart'] = sport.first
                attr['SrcPortEnd'] = sport.last
                # FIXME: attr['SrcPort'] = sport.first
            else:
                attr['SrcPortStart'] = PORT_MIN
                attr['SrcPortEnd'] = PORT_MAX
                # FIXME: attr['SrcPort'] = PORT_MIN

            dport = protocol.dport
            if dport:
                attr['DstPortStart'] = dport.first
                attr['DstPortEnd'] = dport.last
                attr['DstPort'] = dport.first
            else:
                attr['DstPortStart'] = PORT_MIN
                attr['DstPortEnd'] = PORT_MAX
                attr['DstPort'] = PORT_MIN

            if application:
                attr['AppName'] = application.path

            if operating_system:
                attr['OsName'] = operating_system.name
                if operating_system.version:
                    attr['OsVersion'] = operating_system.version
                if operating_system.release:
                    attr['OsRelease'] = operating_system.release

            # TODO: Check the result is ok when specifying multiple durations/periodicities
            if timerange:
                attr['TimeRange'] = timerange.id

            attr.update(common_attr)
            yield attr

    def formatValue(self, value):
        # Encode Python value to LDAP format (UTF-8 string or list of UTF-8 strings)
        if isinstance(value, unicode):
            return value.encode("UTF-8")
        elif isinstance(value, (int, long)):
            return str(value)
        elif isinstance(value, (list, tuple)):
            return tuple(self.formatValue(item) for item in value)
        else:
            assert isinstance(value, str), repr(value)
            return value

    def createRule(self, rules, dn, attr):
        for key, value in attr.iteritems():
            value = self.formatValue(value)
            attr[key] = value
        rules.append((dn, attr))

class LdapConnection(Logger):
    def __init__(self, logger, config):
        Logger.__init__(self, "ldap", parent=logger)
        self.basedn = config['basedn']
        try:
            uri = 'ldap://%s:%s' % (config['host'], config['port'])
            self.cursor = initialize(uri)
            self.cursor.simple_bind_s(config['username'], config['password'])
        except ldap_error, err:
            self.raiseError(err)

    def raiseError(self, err):
        info = err.args[0]
        message = toUnicode(info['desc'])
        if 'info' in info:
            message += u"; %s" % toUnicode(info['info'])
        if 'matched' in info:
            matched = toUnicode(info['matched'])
            message += u" (%s)" % matched
        raise RulesetError(tr("LDAP error: %s"), message)

    def searchRules(self):
        result = self.cursor.search(
            self.basedn, SCOPE_SUBTREE,
            '(objectClass=NuAccessControlList)')

        while True:
            result_type, data = self.cursor.result(result, 0)

            if data == []:
                break
            assert len(data) == 1
            cn, attr = data[0]
            yield (cn, attr)

    def applyRules(self, rules):
        for dn, attr in self.searchRules():
            self.cursor.delete_s(dn)
        for dn, attr in rules:
            modlist = addModlist(attr)
            self.cursor.add_s(dn, modlist)

def ldapRules(context, component, ruleset, rule_type, identifiers):
    logger = ContextLoggerChild(context, component)
    result = ApplyRulesResult(logger)

    if rule_type == 'acls-ipv6':
        rules = ruleset.acls_ipv6
    elif rule_type == 'acls-ipv4':
        rules = ruleset.acls_ipv4
    else:
        # NuFW (LDAP) doesn't authenticate NAT rules
        raise RulesetError(tr("LDAP doesn't support rule type: %s"), repr(rule_type))
    if identifiers:
        rules = [ rules[id] for id in identifiers ]
    else:
        rules = rules

    ldap = WriteLdapRules(logger, component.config['ldap'])
    with TemplateInstanciation(ruleset):
        rules = filterRules(result, rules)

        lines = []
        for dn, attr in ldap.createRules(rules):
            lines.append(unicode(dn))
            attrs = attr.items()
            attrs.sort(key=lambda item: item[0])
            for key, value in attrs:
                lines.append(u"  %s=%r" % (key, value))
            lines.append(u"")
        xmlrpc = result.exportXMLRPC()
        xmlrpc['ldap'] = lines
        return xmlrpc

