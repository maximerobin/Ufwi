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

from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.threads import deferToThread

from ufwi_rpcd.common import EDENWALL
from ufwi_rpcd.common.getter import (getBoolean, getUnicode, getInteger,
    getList, getTuple)
from ufwi_rpcd.backend import tr, Component
from ufwi_rpcd.backend.logger import ContextLoggerChild
from ufwi_rpcd.common.multisite import MULTISITE_MASTER, MULTISITE_SLAVE
from ufwi_rpcd.core import events
from ufwi_rpcd.core.context import Context

from ufwi_conf.common.netcfg import deserializeNetCfg

from ufwi_ruleset.version import VERSION
from ufwi_ruleset.common.roles import RULESET_FORWARD_WRITE_ROLES
from ufwi_ruleset.config import RULESET_DIR

from ufwi_ruleset.forward.iptables import iptablesRules
from ufwi_ruleset.forward.ldap_rules import ldapRules
from ufwi_ruleset.forward.ruleset import Ruleset
from ufwi_ruleset.forward.ruleset_loader import checkRulesetName
from ufwi_ruleset.forward.ruleset_list import (
    rulesetList, rulesetDownload, rulesetUpload, rulesetDelete)
from ufwi_ruleset.forward.error import RulesetError
from ufwi_ruleset.forward.apply_rules import applyRulesDefer, consistencyEngine, reapplyLastRuleset, LOCK_RULESET
from ufwi_ruleset.forward.last_ruleset import lastRulesetApplied
from ufwi_ruleset.forward.parameters import RulesetConfig
from ufwi_ruleset.forward.template import getMissingLinks
from ufwi_ruleset.forward.client import Client
if EDENWALL:
    from ufwi_ruleset.forward.multisite import (applyMultisite,
        checkMultisiteTypeValue, MULTISITE_TEMPLATE_NAME)

def getIntegerList(value):
    return getList(getInteger, value)

class RulesetComponent(Component):
    """
    Ruleset: manage FORWARD rules of the firewall.
    """

    NAME = "ufwi_ruleset"
    VERSION = VERSION
    API_VERSION = 2
    REQUIRES = ("network", "config")
    # for the HA: "ha" and "nurestore" are also required
    OPEN_SERVICES = set((
        # Stateless services
        # (eg. don't need to open a ruleset)
        'setupClient', 'setFusion',
        "rulesetDownload", "rulesetUpload",
        "rulesetList", "templateList",
        "rulesetDelete", "templateDelete",
        "getConfig", "setConfig",
        "productionRules", "applyMultisite",
        'getMissingLinks', 'reapplyLastRuleset',
        'runtimeFiles', 'runtimeFilesModified',
    ))
    ROLES = {
        'ruleset_read': set((
            'setupClient', 'setFusion', 'getConfig',
            'rulesetOpen', 'rulesetClose',
            'rulesetDownload', 'rulesetList', 'productionRules',
            'getChain', 'getCustomRules', 'getMissingLinks',
            'genericLinksGet', 'getObjects', 'getRule', 'getRules',
            'rulesetAttributes', 'getDefaultDecisions',
            'iptablesRules', 'ldapRules',
            'consistencyEngine',
            'undoState',
        )),
        'ruleset_write': set(('@ruleset_read',
            'setConfig',
            'rulesetCreate', 'rulesetUpload', 'rulesetDelete', 'rulesetSave', 'rulesetSaveAs',
            'objectCreate', 'objectModify', 'objectTemplatize', 'objectDelete', 'groupCreate',
            'resourceCreate',
            'ruleCreate', 'ruleChange', 'ruleDown', 'ruleUp', 'ruleClone',
            'ruleDelete', 'moveRule',
            'undo', 'redo',
            'genericLinksSet', 'setCustomRules',
            'setDefaultDecisions',
            'addTemplate', 'removeTemplate',
            'applyRules', 'reapplyLastRuleset',
            'ufwi_confSync',
        )),
        'multisite_read': set(('@ruleset_read',)),
        'multisite_write': set(('@ruleset_write',
            'applyMultisite',
        )),
    }
    ACLS = {
        # service required for the HA synchronization
        'ha': set(('ufwi_rulesetExport',)),
        'network': set(('getNetconfig',)),
    }

    def init(self, core):
        self.core = core
        self.notify = core.notify
        self.config = RulesetConfig(self)
        if core.config.getboolean('CORE', 'use_edenwall'):
            self.input_output_rules = core.conf_get_var_or_default(
                'ufwi_ruleset', 'input_output_rules',
                default=False, type='bool')
        else:
            self.input_output_rules = True
        self.ufwi_ruleset_context = Context.fromComponent(self)
        events.connect('ufwi_rpcdServerStarted', self._ufwi_rpcdStarted)

    def _ufwi_rpcdStarted(self):
        if self.core.hasComponent(self.ufwi_ruleset_context, 'ha'):
            self.notify.connect(self.name, "apply", self._syncHA)

    def getClient(self, context):
        session = context.getSession()
        if 'ufwi_ruleset_client' not in session:
            client = Client({})
            session['ufwi_ruleset_client'] = client
        return session['ufwi_ruleset_client']

    def getFusion(self, context, fusion):
        if fusion is None:
            client = self.getClient(context)
            return client.fusion
        else:
            return getBoolean(fusion)

    def hasRuleset(self, context):
        return ('ufwi_ruleset' in context.getSession())

    def getRuleset(self, context, raise_error=True):
        session = context.getSession()
        if raise_error:
            return session['ufwi_ruleset']
        else:
            return session.get('ufwi_ruleset', None)

    def service_setupClient(self, context, attr):
        """
        Setup the client: attr = {
            'version': client_version,
            'mode': 'GUI' (default) or 'CLI',
        }.

        Return {'version': server_version}.
        """
        client = Client(attr)
        session = context.getSession()
        session['ufwi_ruleset_client'] = client
        if 'ufwi_ruleset' in session:
            ruleset = session['ufwi_ruleset']
            ruleset.client = client
        return client.exportXMLRPC()

    def service_setFusion(self, context, enabled):
        """
        Enable or disable the fusion.
        """
        fusion = getBoolean(enabled)
        client = self.getClient(context)
        ruleset = self.getRuleset(context, raise_error=False)
        return client.setFusion(fusion, ruleset)

    def service_setConfig(self, context, config):
        """
        Set the configuration
        """
        self.config.setConfig(self, config)
        return self.config.exportXMLRPC()

    def service_getConfig(self, context):
        """
            Get configuration dictionary
        """
        return self.config.exportXMLRPC()

    @inlineCallbacks
    def service_rulesetOpen(self, context, filetype, name):
        """
        Open a ruleset or a template (if is_template is True).
        """
        filetype = getUnicode(filetype)
        name = getUnicode(name)
        checkRulesetName(name)
        client = self.getClient(context)
        logger = ContextLoggerChild(context, self)

        self.info(context, 'Open the ruleset "%s"' % name)
        data = yield self.core.callService(self.ufwi_ruleset_context, 'network', 'getNetconfig')
        netcfg = deserializeNetCfg(data)

        read_only = not any(context.hasRole(role) for role in RULESET_FORWARD_WRITE_ROLES)
        if EDENWALL \
        and (not read_only) \
        and (filetype == "template") \
        and (self.core.getMultisiteType() == MULTISITE_SLAVE):
            read_only = True
        ruleset = Ruleset(self, logger, netcfg,
            read_only=read_only, client=client)
        result = ruleset.load(logger, filetype, name)

        if not read_only:
            self.core.lock_manager.acquire(context, LOCK_RULESET)
        self._saveRuleset(context, ruleset)
        returnValue(result)

    def service_rulesetDownload(self, context, filetype, name):
        """
        Download a ruleset (filetype="ruleset") or a template
        (ruleset="template"). Return the file content as an encoded byte
        string, use decodeFileContent() to decode the content.
        """
        name = getUnicode(name)
        filetype = getUnicode(filetype)
        self.info(context, 'Download the %s: "%s"' % (filetype, name))
        return rulesetDownload(filetype, name)

    @inlineCallbacks
    def service_rulesetUpload(self, context, filetype, filename, content):
        """
        Upload a new ruleset or template:
         - filetype: "ruleset" or "template"
         - filename: input filename
         - content: file content encoded by encodeFileContent()

        Return the ruleset name.
        """
        filetype = getUnicode(filetype)
        filename = getUnicode(filename)
        content = getUnicode(content)
        self.info(context, 'Upload a new %s: filename="%s"' % (filetype, filename))
        logger = ContextLoggerChild(context, self)

        data = yield self.core.callService(self.ufwi_ruleset_context, 'network', 'getNetconfig')
        netcfg = deserializeNetCfg(data)
        result = rulesetUpload(self, logger, filetype, filename, content, netcfg)
        returnValue(result)

    @inlineCallbacks
    def service_rulesetCreate(self, context, filetype, base_template):
        """
        Create a new ruleset based on a template. Use base_template='' to
        ignore the base template.
        """
        self.info(context, 'Create a new ruleset')
        if EDENWALL:
            multisite_type = self.core.getMultisiteType()
            base_template = checkMultisiteTypeValue(multisite_type, filetype, base_template)
        client = self.getClient(context)
        logger = ContextLoggerChild(context, self)

        data = yield self.core.callService(self.ufwi_ruleset_context, 'network', 'getNetconfig')
        netcfg = deserializeNetCfg(data)

        ruleset = Ruleset(self, logger, netcfg, client=client)
        result = ruleset.create(logger, filetype, netcfg, base_template=base_template)
        if not ruleset.read_only:
            self.core.lock_manager.acquire(context, LOCK_RULESET)
        self._saveRuleset(context, ruleset)

        returnValue(result)

    def service_rulesetAttributes(self, context):
        """
        Get attributes of the current ruleset. Return a dictionary.  See
        Ruleset.getAttributes() for the keys.
        """
        ruleset = self.getRuleset(context)
        return ruleset.exportXMLRPC()

    def _saveRuleset(self, context, ruleset):
        session = context.getSession()
        session['ufwi_ruleset'] = ruleset
        session.save()

    def saveSession(self, context):
        context.getSession().save()

    def service_resourceCreate(self, context, restype, parent, attr, fusion=None):
        """
        Create new host or network resource (depending on the IP prefix
        length):

         - restype: resource type (unicode string)
         - parent: parent resource identifier (unicode string)
         - id: resource identifier (unicode string)
         - argument: IP address for network/host, host name or the
           interface name (value depends on the resource type)

        Use parent=address=empty string for a new interface.
        """
        restype = getUnicode(restype)
        parent = getUnicode(parent)
        fusion = self.getFusion(context, fusion)
        resources = self.getRuleset(context).resources
        updates = resources.serviceCreate(restype, parent, attr, fusion)
        self.saveSession(context)
        return updates

    def service_objectTemplatize(self, context, library, identifier, fusion=None):
        """
        Convert an object to a generic.
        """
        identifier = getUnicode(identifier)
        fusion = self.getFusion(context, fusion)
        library = self.getRuleset(context).getLibrary(library)
        object = library[identifier]
        updates = library.templatize(object, fusion)
        self.saveSession(context)
        return updates

    def service_groupCreate(self, context, id, library, objects):
        """
        Create a new group of objects:
            - id : unicode string of the group identifier
            - library : name of the library that stores this group ("applications", "protocols" ...)
            - objects: list of object identifiers contained in the group
        """
        id = getUnicode(id)
        objects = getList(getUnicode, objects)
        library = self.getRuleset(context).getLibrary(library)
        attr = {'id': id, 'objects': objects}
        updates = library.createGroup(attr)
        self.saveSession(context)
        return updates

    def service_ruleCreate(self, context, rule_type, values):
        """
        Create a new ACL: values is a dictionary of ACL attributes.
        rule_type:

         - acls-ipv4: IPv4 ACL
         - acls-ipv6: IPv6 ACL
         - nats: NAT (IPv4)

        Mandatory attributes:

         - input, output: interface identifier (unicode) list,
           eg. "eth0"
         - sources, destinations: resource identifier (unicode) list,
           eg. ["my host"]
         - protocols: protocol identifier list (unicode),
           eg. ["FTP", "DNS"]
         - decision: "ACCEPT", "DROP" or "REJECT"
         - log: boolean

        Optional attributes:

         - enabled: boolean (default: True)
         - comment: unicode (default: empty comment)
         - position: integer, position in the rule chain

        Example: ::

           aclCreate({
               'enabled': True,
               'decision': "ACCEPT",
               'sources': ["INTERNET"],
               'destinations': ["web server 1", "web server 2"],
               'protocols': ["HTTP", "HTTPS"],
           })
        """
        ruleset = self.getRuleset(context)
        rules = ruleset.getRuleList(rule_type)
        updates = rules.create(values)
        self.saveSession(context)
        return updates

    def service_ruleClone(self, context, rule_type, acl_id):
        """
        Clone an ACL: acl_id is its identifier.
        """
        acl_id = getInteger(acl_id)
        ruleset = self.getRuleset(context)
        rules = ruleset.getRuleList(rule_type)
        updates = rules.clone(acl_id)
        self.saveSession(context)
        return updates

    def moveRule(self, context, rule_type, identifier, delta):
        identifier = getInteger(identifier)
        rules = self.getRuleset(context).getRuleList(rule_type)
        rule = rules[identifier]
        chain = rules.getAclChain(rule)
        new_order = chain.getOrder(rule) + delta
        updates = rules.moveAt(rule, new_order)
        self.saveSession(context)
        return updates

    def service_ruleUp(self, context, rule_type, identifier):
        """
        Move ACLs up.
        """
        return self.moveRule(context, rule_type, identifier, -1)

    def service_ruleDown(self, context, rule_type, identifier):
        """
        Move ACLs down.
        """
        return self.moveRule(context, rule_type, identifier, 1)

    def service_moveRule(self, context, rule_type, identifier, new_order):
        """
        Move a rule to the new specific order (in the same chain).
        """
        identifier = getInteger(identifier)
        rules = self.getRuleset(context).getRuleList(rule_type)
        updates = rules.moveAt(rules[identifier], new_order)
        self.saveSession(context)
        return updates

    def service_ruleDelete(self, context, rule_type, identifiers):
        """
        Delete ACLs using a list of ACL identifiers (int).
        Return number of deleted ACLs.
        """
        acls = self.getRuleset(context).getRuleList(rule_type)
        identifiers = getIntegerList(identifiers)
        updates = acls.delete(identifiers)
        self.saveSession(context)
        return updates

    def service_getObjects(self, context, library, fusion=None):
        """
        Returns the list of all objects of a library.
        If fusion is True, merge generic and physical objects.
        """
        library = getUnicode(library)
        fusion = self.getFusion(context, fusion)
        ruleset = self.getRuleset(context)
        library = ruleset.getLibrary(library)
        return library.exportXMLRPC(fusion)

    def service_objectDelete(self, context, lib_name, identifier):
        """
        Delete an object from the library lib_name using its identifier (unicode string).
        """
        identifier = getUnicode(identifier)
        library = self.getRuleset(context).getLibrary(lib_name)
        updates = library.delete(identifier)
        self.saveSession(context)
        return updates

    def service_objectCreate(self, context, library, attr, fusion=None):
        """
        Create a new object in a library from a dict of attributes
        """
        library = getUnicode(library)
        fusion = self.getFusion(context, fusion)
        library = self.getRuleset(context).getLibrary(library)
        result = library.createObject(attr, fusion)
        self.saveSession(context)
        return result

    def service_objectModify(self, context, library, identifier, attr, fusion=None):
        """
        Modify an object:
         - library (unicode): name of the object library (eg. "protocols")
         - identifier (unicode or int): object identifier (int for rules,
           unicode for other objects)
         - attr (dict): object attributes

        If a (mandatory or optional) attribute is not set in attr, the
        attribute value is unchanged.
        """
        identifier = getUnicode(identifier)
        library = getUnicode(library)
        fusion = self.getFusion(context, fusion)

        ruleset = self.getRuleset(context)
        library = ruleset.getLibrary(library)
        object = library[identifier]

        updates = library.modifyObject(object, attr, fusion)
        self.saveSession(context)
        return updates

    def service_getChain(self, context, rule_type, key, fusion=None):
        """
        Get ACLs as a chain where chain is:
         - (unicode, unicode) for a FORWARD chain,
         - "INPUT" for the input ACLs
         - "OUTPUT for the output ACLs

        Return a list of ACLs. See getRule() service for the format of each ACL.
        """
        ruleset = self.getRuleset(context)
        if isinstance(key, (tuple, list)):
            key = getTuple(getUnicode, key)
        else:
            key = getUnicode(key)
        fusion = self.getFusion(context, fusion)
        rules = ruleset.getRuleList(rule_type)
        chain = rules.getChain(key)
        return chain.exportXMLRPC(fusion)

    def service_getRules(self, context, rule_type, fusion=None):
        """
        Get all rules. Arguments :

         - rule_type: possible values are

           * "acls-ipv4" (IPv4 ACL)
           * "acls-ipv6" (IPv6 ACL)
           * "nats" (IPv4 NAT)

         - fusion (boolean): if True, replace generic networks / user groups by
           physical networks / user groups

        Result is list of (chain identifier, list of rules) where chain
        identifier possible values are:

         - ACL rules: "INPUT", "OUTPUT", (input, output) where input / output
           are interface identifiers (eg. ("eth0", "eth2")).
         - NAT rules: "PREROUTING", "POSTROUTING"

        See getRule() service for the format of one rule.
        """
        rule_type = getUnicode(rule_type)
        fusion = self.getFusion(context, fusion)
        ruleset = self.getRuleset(context)
        rules = ruleset.getRuleList(rule_type)
        return rules.exportXMLRPC(fusion)

    def service_getRule(self, context, rule_type, rule_id, fusion=None):
        """
        Get a ACL or NAT rule. Arguments:

         - rule_type: possible values are

           * "acls-ipv4" (IPv4 ACL)
           * "acls-ipv6" (IPv6 ACL)
           * "nats" (IPv4 NAT)

         - rule_id (integer): rule identifier
         - fusion (boolean): if True, replace generic networks / user groups by
           physical networks / user groups

        Result is a dictionary with the following keys.

        Common keys:

         - mandatory keys

           * id (integer): unique rule identifier
           * mandatory (boolean): True if the rule is mandatory
           * enabled (boolean): ACL is enabled? (bool)
           * sources (list of unicode): List of network identifiers
           * destinations (list of unicode): List of network identifiers

         - optional keys:
           * comment (unicode): Comment

        ACL keys:

         - mandatory keys:

           * decision (unicode): 'ACCEPT', 'DROP' or 'REJECT'
           * protocols (list of unicode): List of protocol identifiers
           * address_type (unicode): IPV4_ADDRESS or IPV6_ADDRESS
           * input (unicode): Identifier of the input interface
           * output (unicode): Identifier of the output interface
           * chain (unicode): 'INPUT', 'OUTPUT' or 'FORWARD'
           * log (boolean): Log connections or not?

         - optional keys:

           * user_groups (list of unicode): List of user group identifiers
           * applications (list of unicode): List of application identifiers
           * operating_systems (list of unicode): List of operating system identifiers
           * periodicities (list of unicode): List of periodicity identifiers
           * durations (list of unicode): List of duration identifiers
           * log_prefix (unciode): Prefix of an log entry

        NAT keys:

         - mandatory keys:

           * filters (list of unicode): List of protocol identifiers
           * nated_sources (list of unicode): List of translated network identifiers
           * nated_destinations (list of unicode): List of translated network identifiers
           * nated_filters (list of unicode): List of translated protocol identifiers
           * chain (unicode): 'PREROUTING' or 'POSTROUTING'

        A rule identifier is only unique in its list. Eg. you can have an IPv4
        ACL and an IPv6 ACL with the same identifier. Use (rule_type, rule_id)
        for a global unique identifier.
        """
        rule_type = getUnicode(rule_type)
        rule_id = getInteger(rule_id)
        fusion = self.getFusion(context, fusion)
        rules = self.getRuleset(context).getRuleList(rule_type)
        rule = rules[rule_id]
        return rule.exportXMLRPC(fusion)

    def service_rulesetSave(self, context):
        """
        Save the ruleset to the disk. Raise an error if the
        ruleset has no filename (it's a new ruleset).

        See also rulesetSaveAs().
        """
        ruleset = self.getRuleset(context)
        if EDENWALL \
        and (ruleset.filetype == "template") \
        and (ruleset.name == MULTISITE_TEMPLATE_NAME) \
        and (self.core.getMultisiteType() == MULTISITE_SLAVE):
            raise RulesetError(tr("You can not edit the multisite template from a slave."))
        ruleset.save()
        self.saveSession(context)
        return True

    def service_rulesetSaveAs(self, context, name):
        """
        Save the ruleset as a new name.

        See also rulesetSave().
        """
        name = getUnicode(name)
        ruleset = self.getRuleset(context)
        result = ruleset.saveAs(name)
        self.saveSession(context)
        return result

    def service_rulesetDelete(self, context, filetype, name):
        """
        Delete the specified ruleset or template.
        """
        name = getUnicode(name)
        filetype = getUnicode(filetype)
        if self.hasRuleset(context):
            ruleset = self.getRuleset(context)
            if ruleset.name == name:
                raise RulesetError(tr("Unable to delete the current rule set!"))
        rulesetDelete(self.core, filetype, name)

    def service_iptablesRules(self, context, rule_type, identifiers, use_nufw):
        """
        iptablesRules(rule_type, identifiers, use_nufw)

        Create iptables rules for ACLs:

         - identifiers: ACL identifiers (list of integers)
         - address_type: "IPv4" or "IPv6"

        Use an empty list as identifiers to generate rules of all ACLs.
        Result is a list of Unicode strings (without "iptables " prefix).
        """
        rule_type = getUnicode(rule_type)
        identifiers = getIntegerList(identifiers)
        use_nufw = getBoolean(use_nufw)
        ruleset = self.getRuleset(context)
        return iptablesRules(context, self, ruleset, rule_type, identifiers, use_nufw)

    def service_ldapRules(self, context, rule_type, identifiers):
        """
        ldapRules(rule_type, identifiers)

        Create LDAP rules for ACLs:

         - identifiers: ACL identifiers (list of integers)
         - address_type: "IPv4" or "IPv6"

        Use an empty list as identifiers to generate rules of all ACLs.
        Result is a list of Unicode strings.
        """
        rule_type = getUnicode(rule_type)
        identifiers = getIntegerList(identifiers)
        ruleset = self.getRuleset(context)
        return ldapRules(context, self, ruleset, rule_type, identifiers)

    def _syncHA(self, event_context):
        try:
            ha_defer = self.core.callService(self.ufwi_ruleset_context, 'ha', 'ufwi_rulesetExport')
            ha_defer.addErrback(self.writeError, "Error on HA synchronization")
            # don't return the Deferred object,
            # because HA shouldn't block applyRules() service
        except Exception, err:
            self.writeError(err, "Error on HA synchronization")

    def service_applyRules(self, context, consistency_error, use_nufw):
        """
        Apply ACLs to iptables and LDAP. Arguments:
         - consistency_error (bool): if True, block on consistency error
         - use_nufw (bool): if True, create LDAP rules and use authentication.
           If False, don't create LDAP rules and ignore all NuFW filtres (user
           group, time, etc.)

        Return is a dictionary with keys:
         - applied (boolean): True if rules are correctly applied
         - errors (list of messages): error messages
         - warnings (list of messages): warning messages
         - consistency_error (boolean): True if the apply failed because of the
           consistency engine

        A message is a tuple (format, arguments), to display it, use: ::

           format % arguments
        """
        if EDENWALL \
        and (self.core.getMultisiteType() == MULTISITE_MASTER):
            raise RulesetError(
                tr("Can not apply rules from a multisite master."))
        use_nufw = getBoolean(use_nufw)
        consistency_error = getBoolean(consistency_error)
        ruleset = self.getRuleset(context)
        return applyRulesDefer(context, self, ruleset, use_nufw, consistency_error)

    def service_consistencyEngine(self, context):
        """
        Run consistency engine. See applyRules() service for the result format.
        """
        ruleset = self.getRuleset(context)
        return consistencyEngine(context, self, ruleset)

    def reapplyLastRuleset(self, netcfg, context):
        return deferToThread(reapplyLastRuleset, netcfg, context, self)

    def service_reapplyLastRuleset(self, context):
        """
        Apply ACLs to iptables and LDAP.
        """
        defer = self.core.callService(self.ufwi_ruleset_context, 'network', 'getNetconfig')
        defer.addCallback(deserializeNetCfg)
        defer.addCallback(self.reapplyLastRuleset, context)
        return defer

    def service_rulesetClose(self, context):
        """
        Close active ruleset without saving changes.
        Use ruleset_write() to save changes to a file.
        """
        read_only = self.getRuleset(context).read_only
        del context.getSession()['ufwi_ruleset']
        if not read_only:
            self.core.lock_manager.release(context, LOCK_RULESET)
        return True

    def service_rulesetList(self, context, filetype):
        """
        Return the list of:
         - filetype="ruleset": rulesets
         - filetype="template": templates

        Return a list of (name, timestamp) where name and timestamp are
        unicode string.
        """
        filetype = getUnicode(filetype)
        return rulesetList(filetype)

    def service_ruleChange(self, context, rule_type, acl_id, new_values):
        """
        Change attributes of an ACL:
         - acl_id: acl identifier (unicode)
         - new_values: dictionary (attribute name => value)
        """
        acl_id = getInteger(acl_id)
        acls = self.getRuleset(context).getRuleList(rule_type)
        acl = acls[acl_id]
        updates = acls.modifyObject(acl, new_values, False)
        self.saveSession(context)
        return updates

    def service_undo(self, context):
        """
        Undo last action, return a tuple of unicode strings:
        (domain, identifier) where identifier can be an empty string.

        Eg. ("acls", "4").
        """
        ruleset = self.getRuleset(context)
        result = ruleset.undoLast()
        self.saveSession(context)
        return result

    def service_redo(self, context):
        """
        Redo last action.
        Return action domain as unicode string (eg. "resources).
        """
        ruleset = self.getRuleset(context)
        result = ruleset.redoLast()
        self.saveSession(context)
        return result

    def service_undoState(self, context):
        """
        Get undo state as tuple of booleans:
        (ruleset_modified, can_undo, can_redo).
        """
        ruleset = self.getRuleset(context)
        return ruleset.undoState()

    def service_getCustomRules(self, context):
        custom = self.getRuleset(context).custom_rules
        return custom.exportXMLRPC()

    def service_setCustomRules(self, context, rules):
        ruleset = self.getRuleset(context)
        ruleset.setCustomRules(rules)

    def service_genericLinksGet(self, context):
        """
        Get generic links.
        """
        links = self.getRuleset(context).generic_links
        return links.exportXMLRPC()

    def service_genericLinksSet(self, context, links):
        """
        Set generic links.
        """
        if EDENWALL \
        and (self.core.getMultisiteType() == MULTISITE_SLAVE):
            raise RulesetError(tr("Can not set generic links from a slave."))
        ruleset = self.getRuleset(context)
        generic = ruleset.generic_links
        updates = generic.setLinksAction(links)
        self.saveSession(context)
        return updates

    def service_productionRules(self, context):
        """
        Get informations about the rules in production as a dictionary with
        keys:

         - timestamp: use parseDatetime() from ufwi_rpcd.common.transport
           to get a datetime object
         - use_nufw: boolean (True if NuFW is used)
         - ruleset (optional): name of the ruleset

        Name is not set if localfw component was used to create the rules
        (without any ruleset).

        Return an empty dict if ufwi_ruleset.apply() nor localfw.apply() was not
        called (if no rules are in production).
        """
        return lastRulesetApplied()

    if EDENWALL:
        def service_applyMultisite(self, context, template_url, generic_links):
            """
            Apply multisite rules:

               1. download template data (if we don't want to remove the template)
               2. replace the template in all rulesets
               3. install new generic links
               4. reapply the last applied ruleset (if a ruleset was applied)

            If any step failed, restore all data to previous state to ensure that
            data are always consistent.
            """
            return applyMultisite(self, context, template_url, generic_links)

    def service_addTemplate(self, context, name):
        """
        Add the specified template to the current ruleset. On duplicate
        identifiers, objects from the ruleset are renamed with suffix (eg.
        "Internet" => "Internet-2").
        """
        if EDENWALL \
        and (self.core.getMultisiteType() == MULTISITE_SLAVE):
            raise RulesetError(tr("Can not add a template from a slave."))
        name = getUnicode(name)
        ruleset = self.getRuleset(context)
        updates = ruleset.addTemplate(self, name)
        self.saveSession(context)
        return updates

    def service_removeTemplate(self, context, name):
        """
        Delete the specified template from the current ruleset. All objects
        from the template are marked as editable and now saved in the ruleset.
        """
        if EDENWALL \
        and (self.core.getMultisiteType() == MULTISITE_SLAVE):
            raise RulesetError(tr("Can not delete a template from a slave."))
        name = getUnicode(name)
        ruleset = self.getRuleset(context)
        updates = ruleset.removeTemplate(name)
        self.saveSession(context)
        return updates

    @inlineCallbacks
    def service_getMissingLinks(self, context, filetype, name, links):
        """
        Check if all generic links are defined for the specified
        ruleset/template "name".

        Return the list of generic links without physical value as a
        dictionary. If the dictionary is empty, all generic links are defined.
        """
        name = getUnicode(name)
        logger = ContextLoggerChild(context, self)
        data = yield self.core.callService(self.ufwi_ruleset_context, 'network', 'getNetconfig')
        netcfg = deserializeNetCfg(data)
        result = getMissingLinks(self, logger, filetype, name, netcfg, links)
        returnValue(result)

    def service_runtimeFiles(self, context):
        """
        list configuration files
        """
        return {
            'deleted': (RULESET_DIR,),
            # FIXME: write an explicit list of all files
            # FIXME: Maybe, export only the production ruleset
            'added': ((RULESET_DIR, 'dir'),),
        }

    def service_runtimeFilesModified(self, context):
        """
        take in account external modifications of runtime files : reload conf.
        """
        return self.core.callService(context, self.NAME, 'reapplyLastRuleset')

    def service_getDefaultDecisions(self, context, rule_type):
        """
        Get the default decisions, rule_type is "acls-ipv4" or "acls-ipv6".

        Result is a dictionary chain => (decision, use_log), with:

         - chain: 'INPUT, 'OUTPUT', or a tuple of the input and output
           interface identifiers, eg. ('DMZ', 'LAN Interface')
         - decision: 'ACCEPT', 'DROP' or 'REJECT'
         - use_log: boolean
        """
        rule_type = getUnicode(rule_type)
        if rule_type not in ("acls-ipv4", "acls-ipv6"):
            raise RulesetError(tr("No default decision is associated with %s rules"), rule_type)
        ruleset = self.getRuleset(context)
        rules = ruleset.getRuleList(rule_type)
        return rules.default_decisions.exportXMLRPC()

    def service_setDefaultDecisions(self, context, rule_type, default_decisions):
        """
        Set the default decisions, rule_type is "acls-ipv4" or "acls-ipv6".

        See getDefaultDecisions() service for the format (dictionary).
        """
        rule_type = getUnicode(rule_type)
        if rule_type not in ("acls-ipv4", "acls-ipv6"):
            raise RulesetError(tr("No default decision is associated with %s rules"), rule_type)
        ruleset = self.getRuleset(context)
        rules = ruleset.getRuleList(rule_type)
        action = rules.default_decisions.setDecisions(default_decisions)
        return ruleset.addAction(action)

    @inlineCallbacks
    def service_ufwi_confSync(self, context):
        """
        Synchronize with ufwi_conf: create new interfaces and networks from the
        ufwi_conf (system) configuration.

        Keep removed interfaces and networks.
        """
        ruleset = self.getRuleset(context)
        data = yield self.core.callService(self.ufwi_ruleset_context, 'network', 'getNetconfig')
        netcfg = deserializeNetCfg(data)
        result = yield ruleset.ufwi_confSync(self, netcfg)
        returnValue(result)

    def checkServiceCall(self, context, service_name):
        if service_name in self.OPEN_SERVICES:
            # Stateless services
            return

        ruleset = self.getRuleset(context, raise_error=False)
        ruleset_open = (ruleset is not None)
        if service_name in ("rulesetOpen", "rulesetCreate", 'templateCreate'):
            if ruleset_open:
                raise RulesetError(
                    tr("There is already an active rule set or template (%s)."),
                    ruleset.name)
        else:
            if not ruleset_open:
                raise RulesetError(
                    tr("You have to create or open a rule set to use the %s() service."),
                    service_name)

