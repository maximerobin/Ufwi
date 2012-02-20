
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

import os
import subprocess

from ufwi_rpcd.common.process import (createProcess, readProcessOutput)
from ufwi_rpcd.backend.process import runCommand

VPN_SUPPORT_STATUSFILE = '/var/run/vpn-support.status'
VPN_SUPPORT_PIDFILE = '/var/run/vpn-support.pid'

def getVpnSupportStatusAndIP(logger):
    process = createProcess(
        logger,
        '/usr/share/ufwi_rpcd/scripts/vpn_support_status_and_ip',
        stdout=subprocess.PIPE)
    # FIXME: use communicateProcess() with a timeout
    return_code = process.wait()
    if return_code == 0:
        return [
            line.strip() for line in readProcessOutput(process.stdout, 2)
            ]

def isVpnSupportRunningOrPending(logger):
    status = getVpnSupportStatusAndIP(logger)[0]
    return status in ('running', 'pending')

def vpnrules(logger, create):
    if create:
        runCommand(logger, ['/sbin/iptables', '-I', 'FORWARD', '-i',
                          'support', '-j', 'DROP'])
        runCommand(logger, ['/sbin/iptables', '-I', 'INPUT', '-i',
                          'support', '-p', 'udp', '--dport', '8080',
                          '-j', 'ACCEPT'])
        for dport in ['8443', '22']:
            runCommand(logger, ['/sbin/iptables', '-I', 'INPUT', '-i',
                              'support', '-p', 'tcp', '--dport', dport,
                              '-j', 'ACCEPT'])
        runCommand(logger, ['/usr/sbin/openvpn',
                          '--writepid', VPN_SUPPORT_PIDFILE,
                          '--daemon', 'vpn-support',
                          '--status', VPN_SUPPORT_STATUSFILE, '10',
                          '--cd', '/etc/vpn-support',
                          '--config', '/etc/vpn-support/support.conf'])
        return
    PID = None
    try:
        with open(VPN_SUPPORT_PIDFILE) as fd:
            PID = int(fd.read().strip())
            if PID == 1:
                return False
    except Exception:
        return False
    if PID is not None:
        runCommand(logger, ['/bin/kill', str(PID)])
        try:
            os.unlink(VPN_SUPPORT_PIDFILE)
            os.unlink(VPN_SUPPORT_STATUSFILE)
        except Exception:
            pass
    for dport in ['8443', '22']:
        runCommand(logger, ['/sbin/iptables', '-D', 'INPUT', '-i',
                          'support', '-p', 'tcp', '--dport', dport,
                          '-j', 'ACCEPT'])
    runCommand(logger, ['/sbin/iptables', '-D', 'INPUT', '-i',
                      'support', '-p', 'udp', '--dport', '8080',
                      '-j', 'ACCEPT'])
    runCommand(logger, ['/sbin/iptables', '-D', 'FORWARD', '-i',
                      'support', '-j', 'DROP'])

def vpn_support_last(logger):
    command = ['/bin/grep', '(sshd:session): session',
               "/var/log/auth.log"]
    process = createProcess(logger, command, stdout=subprocess.PIPE)
    return_code = process.wait()
    if return_code == 0:
        return readProcessOutput(process.stdout, 100)
    else:
        return []

