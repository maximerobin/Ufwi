"""
Copyright (C) 2007-2011 EdenWall Technologies
Written by Pierre Chifflier <p.chifflier AT inl.fr>

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

$Id$
"""
from __future__ import with_statement
from ConfigParser import SafeConfigParser

def writeConfig(core, config):
    """
    Change the ufwi-rpcd configuration: set the new options and write the new
    file (in /etc/ufwi-rpcd/ufwi-rpcd.conf).

    config is a dictionary: section (str)=>values, where values is a
    dictionary: key (str)=>value (str, bool, int, long, float).

    Eg. config={'ssl': {'ca': '/etc/ufwi-rpcd/ca.pem'}}.
    """
    filename = '/etc/ufwi-rpcd/ufwi-rpcd.conf'
    cfgfile = SafeConfigParser()
    cfgfile.read(filename)
    core_config = core.config
    for section, values in config.iteritems():
        if not core_config.has_section(section):
            core_config.add_section(section)
        if not cfgfile.has_section(section):
            cfgfile.add_section(section)
        for key, value in values.iteritems():
            if isinstance(value, bool):
                value = "yes" if value else "no"
            elif isinstance(value, (int, long, float)):
                value = str(value)
            cfgfile.set(section, key, value)
            core_config.set(section, key, value)
    with open(filename, 'w') as fp:
        cfgfile.write(fp)

