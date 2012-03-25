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

from os.path import join as path_join, exists as path_exists

from ufwi_rpcd.common.tools import safeFilenameRegex
from ufwi_rpcd.common import tr

from ufwi_ruleset.forward.error import RulesetError
from ufwi_ruleset.forward.config import ACL_DIR, TEMPLATE_DIR

# Ruleset file format version
#
# Supported versions:
#  - "3.0.1":
#     * IPv4 and IPv6 default decisions
#     * IPsec networks
#  - "3.0.0":
#     * disallow creation of an authenticated ACL using a protocol different
#       than tcp and udp
#  - "3.0dev6":
#     * rename <acls> to <acls_ipv4>
#     * create <acls_ipv6>
#  - "3.0dev5":
#     * introduce next_id attribute to <acls>
#     * store <acl> and <nat> identifier
#     * acl and nat identifier is now composed of two parts:
#       (rule identifier, ruleset identifier)
#     * <duration> rename attribute "duration" to "seconds"
#     * <periodicity> rename attributes date_from, date_to, time_from,
#       time_to to day_from, day_to, hour_from, hour_to
#  - "3.0dev4"
#  - "3.0m3": add custom rules
#
# Old versions, no more supported:
#  - "3.0": first file format version
RULESET_VERSION = "3.0.1"
VALID_VERSIONS = ("3.0m3", "3.0dev4", "3.0dev5", "3.0dev6", "3.0.0", RULESET_VERSION)

# Ruleset name have to be a valid filename
RULESET_NAME_REGEX = safeFilenameRegex(1, 100)

DIRECTORIES = {
    "ruleset": ACL_DIR,
    "template": TEMPLATE_DIR,
}

def checkRulesetName(name):
    if not RULESET_NAME_REGEX.match(name):
        raise RulesetError(
            tr("Invalid rule set name: invalid length or characters (%s)!"),
            name)

def rulesetFilename(filetype, name, check_existing=False):
    checkRulesetName(name)
    directory = DIRECTORIES[filetype]
    filename = path_join(directory, name + '.xml')
    if check_existing and path_exists(filename):
        if filetype == "template":
            message = tr('A template called "%s" already exists!')
        else:
            message = tr('A rule set called "%s" already exists!')
        raise RulesetError(message, name)
    return filename

class LoadRulesetContext:
    def __init__(self, logger):
        self.logger = logger

        # library name => {old identifier => new identifier}
        self.replace_identifiers = {}

        # list of (message: str, arguments: tuple)
        self.warnings = []

    def createFileContext(self, filetype, name, version,
    editable, from_template, ruleset_id):
        return LoadFileContext(self,
            filetype, name, version,
            editable, from_template, ruleset_id)

    def warning(self, message, arguments=tuple()):
        self.logger.warning(message % arguments)
        self.warnings.append((message, arguments))

    def renameIdentifier(self, library, old_id, new_id):
        if library not in self.replace_identifiers:
            self.replace_identifiers[library] = {}
        self.warning(tr('Duplicate identifier: rename "%s" to "%s"'), (old_id, new_id))
        self.replace_identifiers[library][old_id] = new_id

    def getIdentifier(self, library, old_id):
        try:
            return self.replace_identifiers[library][old_id]
        except KeyError:
            return old_id

class LoadFileContext:
    def __init__(self, ruleset_context, filetype, name, version,
    editable, from_template, ruleset_id):
        self.ruleset_context = ruleset_context
        if version not in VALID_VERSIONS:
            raise RulesetError(
                tr('Unknown rule set format version: "%s"!'),
                version)
        self.version = version
        self.editable = editable
        self.from_template = from_template
        # Used for ACL and NAT to compute their identifiers
        self.ruleset_id = ruleset_id

    def renameIdentifier(self, library, old_id, new_id):
        self.ruleset_context.renameIdentifier(library, old_id, new_id)

    def getIdentifier(self, library, old_id):
        return self.ruleset_context.getIdentifier(library, old_id)

    def warning(self, message, arguments=tuple()):
        self.ruleset_context.warning(message, arguments)

