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
from subprocess import PIPE
from ufwi_ruleset.iptables.config import IPTABLES_RESTORE, IP6TABLES_RESTORE
from ufwi_ruleset.iptables import IptablesError
from ufwi_rpcd.backend import tr
import re
from ufwi_rpcd.backend.process import runCommandAsRoot

# "iptables-restore: line 3 failed"
ERROR_REGEX = re.compile("line ([0-9]+) failed")

# 'Error occurred at line: 7'
ERROR2_REGEX = re.compile("Error occurred at line: ([0-9]+)")

# 'iptables-restore v1.3.6: Can't set policy `F' on `ACCEPT' line 16: Bad built-in chain name'
ERROR3_REGEX = re.compile("line ([0-9]+): ")

def searchErrorLine(stderr):
    message = None
    for line in stderr:
        line = line.rstrip()
        if not message:
            message = line

        match = ERROR_REGEX.search(line)
        if match:
            return message, int(match.group(1))

        match = ERROR2_REGEX.search(line)
        if match:
            return message, int(match.group(1))

        match = ERROR3_REGEX.search(line)
        if match:
            return message, int(match.group(1))
    return message, None

def iptablesRestore(logger, filename, ipv6, check_error=True):
    if ipv6:
        logger.warning("Load IPv6 iptables rules from %s" % filename)
    else:
        logger.warning("Load IPv4 iptables rules from %s" % filename)
    if ipv6:
        command = IP6TABLES_RESTORE
    else:
        command = IPTABLES_RESTORE
    process, code = runCommandAsRoot(logger, [command], 90.0, stdin_filename=filename, stderr=PIPE)
    if code == 0:
        return

    # error!
    message, line_number = searchErrorLine(process.stderr)
    iptables = None
    if line_number is not None:
        with open(filename) as rules:
            for index, line in enumerate(rules):
                if (1+index) != line_number:
                    continue
                iptables = line.rstrip()
                break
    command_str = command
    if check_error:
        if iptables:
            raise IptablesError(tr("%s command error on iptables rule (line %s):\n%s"),
                command_str, line_number, repr(iptables))
        else:
            raise IptablesError(tr("%s command exited with code %s: %s"),
                command_str, code, message)
    else:
        if iptables:
            logger.warning("%s command error on iptables rule (line %s):"
                % (command_str, line_number))
            logger.warning(repr(iptables))
        else:
            logger.warning("%s command exited with code %s: %s"
                % (command_str, code, message))

