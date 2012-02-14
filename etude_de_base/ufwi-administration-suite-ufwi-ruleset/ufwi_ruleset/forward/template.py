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

from os import unlink, umask

from ufwi_rpcd.common.logger import LoggerChild
from ufwi_rpcd.common.error import exceptionAsUnicode
from ufwi_rpcd.common.transaction import Transaction

from ufwi_rpcd.backend import tr

from ufwi_ruleset.forward.error import RulesetError
from ufwi_ruleset.forward.ruleset import Ruleset
from ufwi_ruleset.forward.file import File, unlinkQuiet
from ufwi_ruleset.forward.ruleset_loader import rulesetFilename

def replaceTemplate(logger, ruleset, new_template_name):
    templates = ruleset.include_templates.values()
    for template in templates:
        if template.name == new_template_name:
            continue
        if template.parent:
            continue
        logger.info("Remove template %s from ruleset %s"
            % (template.name, ruleset.name))
        ruleset.removeTemplate(template.name)
    if new_template_name \
    and (new_template_name not in ruleset.include_templates):
        logger.info("Add template %s to ruleset %s"
            % (new_template_name, ruleset.name))
        ruleset.addTemplate(logger, new_template_name)

class ReplaceTemplate(Transaction, LoggerChild):
    def __init__(self, logger, component, netcfg, ruleset, template, use_template):
        LoggerChild.__init__(self, logger)
        self.component = component
        self.netcfg = netcfg
        self.ruleset = ruleset  # Ruleset name (str)
        self.template = template
        self.use_template = use_template
        self.filename = rulesetFilename("ruleset", self.ruleset)
        self.old = File(self.filename + ".old", False)

    def save(self):
        umask(0077)
        self.old.copyFrom(self.filename)

    def apply(self):
        self.debug("Replace multisite templates in ruleset %s" % self.ruleset)
        logger = self.getLogger()
        ruleset = Ruleset(self.component, logger, self.netcfg)
        ruleset.load(logger, "ruleset", self.ruleset)
        if self.use_template:
            template = self.template
        else:
            template = None
        replaceTemplate(self.getLogger(), ruleset, template)
        ruleset.write(self.filename)

    def rollback(self):
        self.old.renameTo(self.filename)

    def cleanup(self):
        self.old.unlink(quiet=True)

class WriteTemplate(Transaction, LoggerChild):
    def __init__(self, logger, filename, content):
        LoggerChild.__init__(self, logger)
        self.filename = filename
        self.new = File(self.filename + ".new", False)
        self.old = File(self.filename + ".old", False)
        self.content = content

    def prepare(self):
        umask(0077)
        with self.new.open('wb') as f:
            f.write(self.content)

    def save(self):
        umask(0077)
        self.old.copyFrom(self.filename)

    def apply(self):
        self.critical("Write the new multisite template")
        self.new.renameTo(self.filename)

    def rollback(self):
        if self.old.exist:
            self.old.renameTo(self.filename)
        else:
            unlinkQuiet(self.filename)

    def cleanup(self):
        self.old.unlink(quiet=True)
        self.new.unlink(quiet=True)

class RemoveTemplate(Transaction, LoggerChild):
    def __init__(self, logger, filename):
        LoggerChild.__init__(self, logger)
        self.filename = filename
        self.copy = File(self.filename + ".copy", False)

    def save(self):
        umask(0077)
        self.copy.copyFrom(self.filename)

    def apply(self):
        self.critical("Remove multisite template")
        try:
            unlink(self.filename)
        except IOError, err:
            raise RulesetError(
                tr('Unable to delete the multisite template: %s!'),
                exceptionAsUnicode(err))

    def rollback(self):
        if self.copy.exist:
            self.copy.renameTo(self.filename)
        else:
            unlinkQuiet(self.filename)

    def cleanup(self):
        self.copy.unlink()

def getMissingLinks(component, logger, filetype, name, netcfg, links):
    ruleset = Ruleset(component, logger, netcfg)
    ruleset.load(logger, filetype, name)
    generic_links = ruleset.generic_links
    generic_links.setLinks(links)
    return generic_links.getMissingLinks()

