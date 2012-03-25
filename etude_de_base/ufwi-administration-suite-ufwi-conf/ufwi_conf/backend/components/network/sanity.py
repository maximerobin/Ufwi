#coding: utf-8

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

from os import listdir
from os.path import join
import subprocess

from ufwi_rpcd.common.process import createProcess
from ufwi_rpcd.common.process import waitProcess

IFDOWN_D = "/etc/network/if-down.d"
IFUP_D = "/etc/network/if-up.d"

SAFE_IFUP_D_FILES = (
    'ip',
    'openssh-server'
    )


def check_dangerous_files():
    #check IFDOWN_D is empty
    ifdown_dangerous_files = listdir(IFDOWN_D)

    ifup_dangerous_files = listdir(IFUP_D)
    #check IFDOWN_D contains only SAFE_IFUP_D_FILES:
    for safe_file in SAFE_IFUP_D_FILES:
        if safe_file in ifup_dangerous_files:
            ifup_dangerous_files.remove(safe_file)

    dangerous_files = tuple(
            (
            join(IFDOWN_D, file)
            for file in ifdown_dangerous_files
            )
        ) + tuple(
            (
            join(IFUP_D, file)
            for file in ifup_dangerous_files
            )
        )

    return dangerous_files

def warn_dangerous_files(logger):
    dangerous_files = check_dangerous_files()
    if dangerous_files:
        logger.critical("WARNING, the following files were detected "
        "on your system, and they are potentially harmful. "
        "You might want to delete/save them:")
        for file in dangerous_files:
            logger.critical(' * %s' % file)

def check_if_up(ifname):
    """
    Uses the content of /sys/class/net/lo/operstate
    @type ifname: an interface system name
    @return: bool, str
    @raise IOError: if /sys/class/net/$ifname$/operstate' does not exist
    """
    #here, the exception:
    with open('/sys/class/net/%s/operstate' % ifname, 'r') as fd:
        state = fd.read().strip()

    if state == 'down':
        return False, 'Read %s state: "%s".' % (ifname, state)
    elif state == 'up':
        return True, 'Read %s state: "%s".' % (ifname, state)
    elif state == 'unknown' and ifname == 'lo':
        return True, 'Read %s state: "%s"' % (ifname, state)

    return False, 'Unknown state for interface %s.' % (ifname, state)


def check_and_correct_lo(logger):
    """
    @type logger: logging.Logger
    @return: bool
    """
    try:
        ok, msg = check_if_up('lo')
    except IOError:
        return False

    if ok:
        return True
    logger.critical("%s - Bringing lo up..." % msg)
    process = createProcess(
        logger,
        '/sbin/ip l set lo up'.split(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env={}
        )
    retcode = waitProcess(logger, process, 120)

    try:
        re_ok, re_msg = check_if_up('lo')
    except IOError:
        #FIXME: if we go here, what happened ? Shouldn't we have the problem at the beginning of the function
        return False
    if re_ok:
        logger.info("Could bring lo up!")
        return True

    logger.critical("Could NOT bring lo up!")
    return False

