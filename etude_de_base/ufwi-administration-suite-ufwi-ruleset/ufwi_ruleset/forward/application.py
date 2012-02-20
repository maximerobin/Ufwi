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

from ufwi_ruleset.forward.object import Object
from ufwi_ruleset.forward.attribute import Unicode
from ufwi_ruleset.forward.library import Library
from ufwi_ruleset.forward.error import RulesetError
from ufwi_rpcd.backend import tr
import re

# Match filename path, examples:
# "c:\windows\win.ini"
# "c:\Program Files\Firefox\firefox.exe"
# "*\firefox.exe"
# "/usr/lib/firefox/firefox-bin"
regex = ur"^[a-zA-Z0-9*?.:_ \\/-]*$"
PATH_REGEX = re.compile(regex)

class Path(Unicode):
    def getter(self, app, name, path):
        path = unicode(path)
        if not PATH_REGEX.match(path):
            # FIXME: write application identifier
            raise RulesetError(
                tr('Invalid application path: %s'),
                repr(path))
        return path

class Application(Object):
    XML_TAG = u"application"
    UPDATE_DOMAIN = u'applications'
    path = Path()

    def __init__(self, applications, values, loader_context=None):
        self.ruleset = applications.ruleset
        Object.__init__(self, values, loader_context)

    def __unicode__(self):
        return tr('The application %s') % self.formatID()

class Applications(Library):
    NAME = 'applications'
    ACL_ATTRIBUTE = 'applications'
    XML_TAG = u"applications"
    CHILD_CLASSES = (Application,)

