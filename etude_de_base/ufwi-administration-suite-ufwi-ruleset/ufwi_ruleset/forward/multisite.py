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

# FIXME: Remove debug
DEBUG = False

from os.path import exists

from twisted.internet.threads import deferToThread
from twisted.internet.defer import succeed

from ufwi_rpcd.common.multisite import MULTISITE_SLAVE
from ufwi_rpcd.common.logger import LoggerChild
from ufwi_rpcd.common.transaction import (executeTransactions,
    Transaction, TransactionsList)

from ufwi_rpcd.backend.logger import ContextLoggerChild
from ufwi_rpcd.backend import tr

from ufwi_multisite.slave.master import MULTISITE_CERT_NAME

from ufwi_conf.common.netcfg import deserializeNetCfg
from ufwi_ruleset.common.parameters import NUFW_GATEWAY
from ufwi_ruleset.config import PRODUCTION_RULESET

from ufwi_ruleset.forward.error import RulesetError
from ufwi_ruleset.forward.apply_rules import LOCK_RULESET, ApplyRules
from ufwi_ruleset.forward.generic_links import WriteGenericLinks
from ufwi_ruleset.forward.template import WriteTemplate, RemoveTemplate, ReplaceTemplate
from ufwi_ruleset.forward.file import unlinkQuiet
from ufwi_ruleset.forward.last_ruleset import lastRulesetApplied, SaveRuleset
from ufwi_ruleset.forward.ruleset_loader import rulesetFilename
from ufwi_ruleset.forward.ruleset_list import rulesetList
from ufwi_ruleset.forward.ruleset import Ruleset
from ufwi_ruleset.forward.config import (
    MULTISITE_TEMPLATE_NAME, MULTISITE_TEMPLATE_FILENAME)

def checkMultisiteTypeValue(multisite_type, filetype, parent_template):
    if (multisite_type == MULTISITE_SLAVE) and (filetype == "template"):
        raise RulesetError(tr("You can not create or edit templates from a slave."))
    if multisite_type == MULTISITE_SLAVE:
        if exists(MULTISITE_TEMPLATE_FILENAME):
            parent_template = MULTISITE_TEMPLATE_NAME
        else:
            parent_template = None
    return parent_template

def replaceTemplateTransactions(logger, component, netcfg, template, use_template):
    transactions = [
        ReplaceTemplate(logger, component, netcfg, ruleset, template, use_template)
        for ruleset, timestamp in rulesetList('ruleset')]
    return TransactionsList(transactions)

class ApplyRuleset(Transaction, LoggerChild):
    def __init__(self, logger, component, context, netcfg, name, use_nufw):
        LoggerChild.__init__(self, logger)
        self.context = context
        self.component = component
        self.netcfg = netcfg
        # By default, reuse the production ruleset
        self.ruleset_name = name
        self.filename = PRODUCTION_RULESET
        self.use_nufw = use_nufw

    def setRuleset(self, name):
        # Use a newly created ruleset
        self.ruleset_name = name
        self.filename = None

    def apply(self):
        if not self.ruleset_name:
            self.info("Don't apply rule set (no production rule set)")

        self.info("Apply rule set %s" % self.ruleset_name)
        logger = self.getLogger()
        ruleset = Ruleset(self.component, logger, self.netcfg)
        ruleset.load(logger, "ruleset", self.ruleset_name, filename=self.filename)

        apply = ApplyRules(self.context, self.component, ruleset, self.use_nufw,
            raise_error=True, consistency_error=False)
        apply.applyRules()

class CreateEmptyRuleset(Transaction, LoggerChild):
    def __init__(self, logger, component, netcfg):
        LoggerChild.__init__(self, logger)
        self.component = component
        self.netcfg = netcfg
        self.name_callbacks = []

    def prepare(self):
        self.filename = None
        index = 2
        name = "multisite"
        while exists( rulesetFilename("ruleset", name) ):
            name = "multisite-%s" % index
            index += 1
        self.name = name
        for callback in self.name_callbacks:
            callback(name)

    def apply(self):
        self.error('Create ruleset "%s"' % self.name)
        logger = self.getLogger()
        ruleset = Ruleset(self.component, logger, self.netcfg)
        ruleset.create(logger, "ruleset", self.netcfg, base_template=MULTISITE_TEMPLATE_NAME)
        ruleset.saveAs(self.name)
        self.filename = rulesetFilename("ruleset", self.name)

    def rollback(self):
        if self.filename:
            unlinkQuiet(self.filename)

def _applyMultisiteThread(component, context, template_content, generic_links, netcfg):
    logger = ContextLoggerChild(context, component)
    lock_manager = component.core.lock_manager
    use_template = bool(template_content)
    config = component.config
    use_nufw = (config['global']['firewall_type'] == NUFW_GATEWAY)
    last_ruleset = lastRulesetApplied()
    ruleset_name = last_ruleset.get('ruleset')

    # Create transactions
    transactions = []
    if use_template:
        # Write the new multisite template content
        write_template = WriteTemplate(logger, MULTISITE_TEMPLATE_FILENAME, template_content)
        transactions.append(write_template)
    transactions.append(WriteGenericLinks(generic_links, logger))

    if use_template and (not ruleset_name):
        # There is not production ruleset:
        # create an empty ruleset using the template
        create_empty = CreateEmptyRuleset(logger, component, netcfg)
        transactions.append(create_empty)
    else:
        create_empty = None

    # Replace the template in all existing rulesets
    replace = replaceTemplateTransactions(logger, component, netcfg,
        MULTISITE_TEMPLATE_NAME, use_template)
    transactions.append(replace)

    # Reapply the ruleset
    apply = ApplyRuleset(logger, component, context, netcfg,
        ruleset_name, use_nufw)
    transactions.append(apply)
    if create_empty:
        create_empty.name_callbacks.append(apply.setRuleset)

        # The new ruleset is now the production ruleset
        save = SaveRuleset(None, use_nufw)
        transactions.append(save)
        create_empty.name_callbacks.append(save.setRuleset)

    if (not use_template) and exists(MULTISITE_TEMPLATE_FILENAME):
        # Remove the multisite template
        remove = RemoveTemplate(logger, MULTISITE_TEMPLATE_FILENAME)
        transactions.append(remove)

    lock_manager.acquire(context, LOCK_RULESET)
    try:
        executeTransactions(logger, transactions)
    finally:
        lock_manager.release(context, LOCK_RULESET)

def getNetconfig(data, component, context, template_content, generic_links):
    netcfg = deserializeNetCfg(data)
    return deferToThread(_applyMultisiteThread, component, context, template_content, generic_links, netcfg)

def templateContent(template_content, component, context, generic_links):
    defer = component.core.callService(context, 'network', 'getNetconfig')
    defer.addCallback(getNetconfig, component, context, template_content, generic_links)
    return defer

def applyMultisite(component, context, template_url, generic_links):
    core = component.core
    logger = component

    # FIXME: Remove DEBUG
    if not DEBUG:
        if core.getMultisiteType() != MULTISITE_SLAVE:
            raise RulesetError(tr("Multisite rules must be applied from a slave."))
    else:
        content = open('/var/lib/ufwi_ruleset3/templates/local_ipv6_firewall.xml', 'rb').read()

    logger.critical(context, 'Apply multisite: template_url=%s, generic_links=%s'
        % (template_url, generic_links))
    if not DEBUG:
        if template_url:
            defer = core.callService(context,
                'multisite_transport', 'getFile',
                MULTISITE_CERT_NAME, template_url)
        else:
            defer = succeed(None)
    else:
        defer = succeed(content)
    defer.addCallback(templateContent, component, context, generic_links)
    return defer

