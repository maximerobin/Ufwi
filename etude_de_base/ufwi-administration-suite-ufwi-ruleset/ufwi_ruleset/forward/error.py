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

from ufwi_rpcd.common.error import RULESET
from ufwi_rpcd.backend import ComponentError
from ufwi_ruleset.error import RULESET_FORWARD

class RulesetError(ComponentError):
    def __init__(self, *args, **kw):
        ComponentError.__init__(self, RULESET, RULESET_FORWARD, *args, **kw)

