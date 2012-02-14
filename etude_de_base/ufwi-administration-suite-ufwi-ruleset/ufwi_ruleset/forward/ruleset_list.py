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
from glob import glob
from os.path import join as path_join, basename, exists
from os import unlink, stat
from datetime import datetime

from ufwi_rpcd.common.multisite import MULTISITE_SLAVE
from ufwi_rpcd.common.error import exceptionAsUnicode
from ufwi_rpcd.common.download import encodeFileContent, decodeFileContent
from ufwi_rpcd.backend import tr

from ufwi_ruleset.forward.error import RulesetError
from ufwi_ruleset.forward.ruleset_loader import DIRECTORIES, rulesetFilename
from ufwi_ruleset.forward.ruleset import Ruleset
from ufwi_ruleset.forward.template import replaceTemplate
from ufwi_ruleset.forward.config import (
    MULTISITE_TEMPLATE_NAME, MULTISITE_TEMPLATE_FILENAME)

def rulesetList(filetype):
    """
    List all available:
     - filetype="ruleset": rulesets
     - filetype="template": templates

    This function is a generator creating (name, timestamp) tuples.
    """
    directory = DIRECTORIES[filetype]
    for filename in glob(path_join(directory, '*.xml')):
        name = basename(filename)
        name = name[:-4]
        timestamp = stat(filename).st_mtime
        timestamp = datetime.fromtimestamp(timestamp)
        yield (name, unicode(timestamp))

def rulesetDownload(filetype, name):
    filename = rulesetFilename(filetype, name)
    try:
        with open(filename, 'rb') as fp:
            content = fp.read()
    except IOError, err:
        raise RulesetError(
            tr('Unable to open "%s" (%s): %s!'),
            basename(filename), filetype, exceptionAsUnicode(err))
    return encodeFileContent(content)

def rulesetUpload(component, logger, filetype, input_filename, content, netcfg):

    # Extract ruleset name from the input filename
    name = basename(input_filename)
    if not name.lower().endswith(".xml"):
        raise RulesetError('File extension is not ".xml"!')
    name = name[:-4]

    # Ensure that the ruleset doesn't exist on disk
    rulesetFilename(filetype, name, check_existing=True)

    # Decode the content
    content = decodeFileContent(content)

    # Open the ruleset the check the consistency
    ruleset = Ruleset(component, logger, netcfg, read_only=True)
    ruleset.load(logger, filetype, name, content=content)
    if component.core.getMultisiteType() == MULTISITE_SLAVE:
        if exists(MULTISITE_TEMPLATE_FILENAME):
            template = MULTISITE_TEMPLATE_NAME
        else:
            template = None
        replaceTemplate(logger, ruleset, template)

    # Write the ruleset
    try:
        ruleset.save()
    except IOError, err:
        raise RulesetError(
            tr('Unable to write into the file %s (%s): %s!'),
            basename(ruleset.filename), ruleset.filetype,
            exceptionAsUnicode(err))
    return ruleset.name

def rulesetDelete(core, filetype, name):
    """
    Delete the specified ruleset.
    """
    if (filetype == "template") \
    and (core.getMultisiteType() == MULTISITE_SLAVE):
        raise RulesetError(tr("Can not delete a template from a slave."))

    filename = rulesetFilename(filetype, name)
    try:
        unlink(filename)
    except IOError, err:
        raise RulesetError(
            tr('Unable to delete the file %s (%s): %s!'),
            name, filetype, exceptionAsUnicode(err))

