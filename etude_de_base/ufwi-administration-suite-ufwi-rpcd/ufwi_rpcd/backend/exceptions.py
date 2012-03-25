
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

from ufwi_rpcd.common.error import RPCD
from ufwi_rpcd.backend.error import RpcdError
from ufwi_rpcd.backend.error import RPCD_CONFIG
from ufwi_rpcd.backend.error import CONFIG_ALREADY_APPLYING
from ufwi_rpcd.backend.error import CONFIG_NO_SUCH_KEY

class ConfigError(RpcdError):
    def __init__(self, *args, **kw):
        RpcdError.__init__(self, RPCD, RPCD_CONFIG, *args, **kw)

class DeletedKey(ConfigError):
    def __init__(self, *args, **kw):
        ConfigError.__init__(self, CONFIG_NO_SUCH_KEY, *args, **kw)

class AlreadyApplying(ConfigError):
    def __init__(self, *args, **kw):
        ConfigError.__init__(self, CONFIG_ALREADY_APPLYING, *args, **kw)

