"""
Copyright (C) 2008-2011 EdenWall Technologies
Written by Feth Arezki <f.arezki AT edenwall.com>

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

from atlee_pam import authenticate
from ufwi_rpcd.common import tr
from ufwi_conf.backend.nnd_instance import getclient

from ufwi_conf.backend.unix_service import \
    runCommandAndCheck, \
    RunCommandError

from .error import \
    NoSuchUser, NoSuchGroup, GetentError, AuthError, NNDError

GETENT_BIN = "/usr/bin/getent"

def test_system_user(logger, username):
    cmd = (GETENT_BIN, "passwd", username)
    try:
        runCommandAndCheck(logger, cmd)
    except RunCommandError, err:
        if isinstance(err.status, (str, unicode)):
            status = int(err.status)
        else:
            status = err.status
        if status == 2:
            raise NoSuchUser(username)
        else:
            raise GetentError(username)

def test_user(logger, username, nnd=False):
    """
    synopsys:
        test_user(username)

    service version:
        1

    result:
        In case of success:
            test version, "username", username

        In case of error:
            NoSuchUser if user is not found,
            GetentError otherwise
    """
    version = 1
    if not isinstance(username, (str, unicode)) or len(username) < 1:
        raise TypeError("username expected as a string")
    if nnd:
        client = getclient(logger)
        try:
            if not client.testuser(username):
                raise NoSuchUser(username)
        finally:
            client.quit()
    else:
        test_system_user(logger, username)

    return version, "username", username


def test_system_group(logger, groupname):
    cmd = (GETENT_BIN, "group", groupname)
    try:
        runCommandAndCheck(logger, cmd)
    except RunCommandError, err:
        if isinstance(err.status, (str, unicode)):
            status = int(err.status)
        else:
            status = err.status
        if status == 2:
            raise NoSuchGroup(groupname)
        else:
            raise GetentError(groupname)


def test_group(logger, groupname, nnd=False):
    """
    synopsys:
        test_group(groupname)

    service version:
        1

    result:
        In case of success:
            test version, "groupname", groupname

        In case of error:
            NoSuchGroup if group is not found,
            GetentError otherwise
    """
    version = 1

    if not isinstance(groupname, (str, unicode)) or len(groupname) < 1:
        raise TypeError("groupname expected as a string")

    if nnd:
        client = getclient(logger)
        try:
            if not client.testgroup(groupname):
                raise NoSuchGroup(groupname)
        finally:
            client.quit()
    else:
        #will raise if necessary
        test_system_group(logger, groupname)
    return version, "groupname", groupname

def test_auth(logger, username, password, nnd=False):
    """
    synopsys:
        test_auth(username, password)

    service version:
        1

    result:
        In case of success:
            test version, "auth", username

        In case of error:
            AuthError
    """
    version = 1
    if nnd:
        client = getclient(logger)
        try:
            #raises if incorrect
            try:
                client.auth2(username, password)
            except Exception, err:
                raise AuthError(username)
        finally:
            client.quit()
    elif not authenticate(username, password, service="nuauth"):
        raise AuthError(username)

    return version, "auth", username

def canconnectnnd(client, socket):
    if client.connect(filename=socket) is None:
        raise NNDError(tr("Could not connect to NND daemon"))
    return "ok"

