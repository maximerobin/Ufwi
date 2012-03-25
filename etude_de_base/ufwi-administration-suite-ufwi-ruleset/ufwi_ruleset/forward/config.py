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

from os.path import join as path_join
from ufwi_ruleset.config import RULESET_DIR

GENERIC_LINKS_XML = path_join(RULESET_DIR, 'generic_links.xml')
ACL_DIR = path_join(RULESET_DIR, 'rulesets')
TEMPLATE_DIR = path_join(RULESET_DIR, 'templates')
LIBRARY_FILENAME = path_join(RULESET_DIR, 'library.xml')
RULES_FILENAME = path_join(RULESET_DIR, 'rules.pickle')

MULTISITE_TEMPLATE_NAME = "multisite"
MULTISITE_TEMPLATE_FILENAME = path_join(TEMPLATE_DIR, MULTISITE_TEMPLATE_NAME + ".xml")

