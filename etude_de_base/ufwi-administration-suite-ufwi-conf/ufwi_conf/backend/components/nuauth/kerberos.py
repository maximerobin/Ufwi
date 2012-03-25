# -*- coding: utf-8 -*-

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


from subprocess import PIPE

from ufwi_rpcd.common.config import serializeElement
from ufwi_rpcd.common.process import readProcessOutput
from ufwi_rpcd.common.process import createProcess

from .error import INVALID_KEYTAB
from .error import NuauthException

def parse_ktutil_list(output):
    #TODO: do more ?
    #note: output is a list of lines
    return serializeElement(output)

def readKeytab(logger, keytab_filename):
    #check the file syntaxically:
    cmd = ('/usr/sbin/ktutil', '-k', keytab_filename, 'list')

    #except ProcessError
    process = createProcess(logger, cmd, stdout=PIPE, stderr=PIPE, env={})
    return_code = process.wait()

    if return_code != 0:
        stderr = readProcessOutput(process.stderr, -1)
        raise NuauthException(INVALID_KEYTAB, "This keytab is unparseable:%s" % stderr)

    stdout = readProcessOutput(process.stdout, -1)
    return stdout

def parseKeytab(logger, keytab_filename):
    output = readKeytab(logger, keytab_filename)
    return parse_ktutil_list(output)

