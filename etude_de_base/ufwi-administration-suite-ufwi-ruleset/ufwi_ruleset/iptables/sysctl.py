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
from ufwi_rpcd.backend.process import runCommandAsRoot
from ufwi_ruleset.forward.error import RulesetError
from ufwi_rpcd.backend import tr

SYSCTL = u'/sbin/sysctl'

def sysctlGet(key):
    key = ['', 'proc', 'sys'] + key.split('.')
    filename = '/'.join(key)
    with open(filename, 'r') as fp:
        line = fp.readline()
    return line.rstrip()

def sysctlSet(logger, key, value):
    command = [SYSCTL, u"-n", u"-q", u"-w", u"%s=%s" % (key, value)]
    process, code = runCommandAsRoot(logger, command)
    if code != 0:
        raise RulesetError(
            tr("sysctl error: unable to set %s value to %s! (exit code %s)"),
            key, value, code)

