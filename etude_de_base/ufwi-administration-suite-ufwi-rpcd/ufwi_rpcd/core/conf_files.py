"""
Copyright (C) 2007-2011 EdenWall Technologies

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
from ConfigParser import NoOptionError, NoSectionError

RPCD_DEFAULT_CONF = '/etc/ufwi-rpcd/default.ufwi-rpcd.conf'
RPCD_CUSTOM_CONF = '/etc/ufwi-rpcd/ufwi-rpcd.conf'

RPCD_CONF_FILES = (
    RPCD_DEFAULT_CONF,
    RPCD_CUSTOM_CONF,
)

def get_var_or_default(config, section, value, default, typename):
    try:
        if typename == "bool":
            return config.getboolean(section,value)
        return config.get(section,value)
    except (NoOptionError, NoSectionError):
        return default

