
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
from ufwi_rpcd.common.process import createProcess
from ufwi_rpcd.common.process import readProcessOutput
from ufwi_conf.common.resolvcfg import deserialize, ResolvError

def dig(logger, defaultserver=None, server=None, query=None):

    if server in (None, u''):
        assert defaultserver is not None
        server = defaultserver

    if query in (None, u''):
        cmd = ('/usr/bin/dig', '@' + server)
    else:
        cmd = ('/usr/bin/dig', query, '@' + server)

    #except ProcessError
    process = createProcess(logger, cmd, stdout=PIPE, stderr=PIPE, env={})
    return_code = process.wait()

    if return_code != 0:

        if return_code == 9:
            raise ResolvError("Unreachable server")

        stderr = readProcessOutput(process.stderr, 10)
        errmsg = '\n'.join(stderr)
        raise ResolvError(errmsg)

    stdout = readProcessOutput(process.stdout, 500)
    return stdout

def parseDigOutput(output):
    #TODO: do better ?
    #note: output is a list of lines
    return True, "Resolution success"

def boolean_dig(logger, **kwargs):
    try:
        dig(**kwargs)
    except Exception:
        return False
    else:
        return True

