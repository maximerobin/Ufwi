#coding: utf-8

"""
The config to connect to radius servers
"""

# $Id$

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

from ufwi_rpcd.common import tr
from .abstract_cfg import AbstractConf
from .process import createProcess
from .process import ProcessError
from .process import waitProcess
from .validators import check_ip_or_domain
from .validators import check_port

ACCESS_GRANTED = "ACCESS_GRANTED"
ACCESS_DENIED = "ACCESS_DENIED"
RADTEST_EXE = "/usr/bin/radtest"

class RadiusServer(AbstractConf):
    """
    Configuration class for connecting to a single radius server
    """

    ATTRS = """
        server
        port
        secret
        timeout
    """.split()
    #pylint:generated-members:``server,port,secret,timeout``

    DATASTRUCTURE_VERSION = 1

    def __init__(self, server='', port=1812, secret='', timeout=3):
        """
        server can be any reachable server: IP or fqdn are valid
        """
        AbstractConf.__init__(self)

        #happy pylint
        #self.server = self.port = self.secret = self.timeout = None

        self._setLocals(locals())

    def isValid(self):
        ok, msg = self.isValidWithMsg()
        del msg
        return ok

    def server_string(self):
        return "%s:%s" % (self.server, self.port)

    def isValidWithMsg(self):
        if not check_ip_or_domain(self.server):
            return (
                False, "Invalid server configuration: %s" % unicode(self.server)
                )
        if not check_port(self.port):
            return False, "Invalid port specification " + unicode(self.port)
        if not isinstance(self.secret, (str, unicode)) or len(self.secret) == 0:
            return False, "Blank shared secret?"
        try:
            timeout = int(self.timeout)
        except ValueError:
            ok = False
        else:
            ok = timeout > 0
        if not ok:
            return False, "Timeout must be a positive integer"

        return True, "Valid server configuration"

    def setPort(self, value):
        try:
            self.port = int(
                unicode(value)
                )
        except:
            self.port = unicode(value)

    def setSecret(self, value):
        self.secret = unicode(value)

    def setTimeout(self, value):
        try:
            self.timeout = int(
                unicode(value)
                )
        except:
            self.timeout = value

    def setServer(self, value):
        self.server = unicode(value)


    def test(self, logger, user, password):
        return radtest_conf(logger, user, password, self)

class RadiusConf(AbstractConf):
    """
    Configuration class wrapping several connections to radius servers
    """

    ATTRS = """
        servers
    """.split()

    DATASTRUCTURE_VERSION = 1

    # servers : list of RadiusServer

    def __init__(self, servers=None):
        """
        The real 'servers' default value is of an empty list
        """
        if servers is None:
            servers = []
        else:
            RadiusConf.__type_check_servers(servers)

        AbstractConf.__init__(self)

        #happy pylint
        self.servers = None

        self._setLocals(locals())

    @staticmethod
    def __type_check_servers(servers):
        """
        TypeError in case of an error
        """
        if not isinstance(servers, list):
            raise TypeError("Expecting a list of servers, got: " + unicode(type(servers)))
        for server in servers:
            if not isinstance(server, RadiusServer):
                raise TypeError("Unexpected server object type: " + unicode(type(server)))

    @staticmethod
    def defaultServer():
        """
        An invalid (some values are missing) default server conf
        """
        return RadiusServer()

    @staticmethod
    def defaultConf():
        server = RadiusConf.defaultServer()
        return RadiusConf([server,])

    def isValidWithMsg(self):
        if len(self.servers) == 0:
            return False, "Please configure at least one radius server"

        try:
            RadiusConf.__type_check_servers(self.servers)
        except TypeError, err:
            return False, err.args[0]

        return True, "All radius server configurations are valid"

def _parse_radtest(stdout):
    for line in stdout.split("\n"):
        if line.startswith("rad_recv:"):
            #rad_recv: Access-Reject packet from host 192.168.33.190 port 1812, id=94, length=20
            if line.startswith("rad_recv: Access-Accept packet"):
                return True, ACCESS_GRANTED
            elif line.startswith("rad_recv: Access-Reject packet"):
                return False, ACCESS_DENIED
            else:
                return False, line

    #No line starts with rad_recv!
    return False, "Could not reach server"

def radtest(logger, user, password, server_and_port, shared_secret, timeout=3, nas_port=0):
    """
    server_and_port is expected as "192.168.0.1" or "192.168.0.1:1812"
    """
    if not user:
        return False, tr("This parameter cannot be empty: 'user'.")
    if not password:
        return False, tr("This parameter cannot be empty: 'password'.")
    if not shared_secret:
        return False, tr("This parameter cannot be empty: 'shared secret'.")
    if not isinstance(nas_port, int):
        return False, tr("This parameter should be an integer: 'nas port'")
    nas_port = unicode(nas_port)

    process = createProcess(logger,
        (RADTEST_EXE, user, password, server_and_port, nas_port, shared_secret),
        cmdstr="%s <user> <password> %s %s <shared_secret>" \
            % (RADTEST_EXE, server_and_port, nas_port),
        stdout=PIPE, stderr=PIPE)
    try:
        exit_status = waitProcess(logger, process, timeout)
    except ProcessError:
        return False, 'Timeout reached, probably wrong secret'
    stdout = process.stdout.read()
    stderr = process.stderr.read()

    if exit_status != 0:
        return False, "stdout: %s\nstderr:%s" % (stdout, stderr)

    return _parse_radtest(stdout)

def radtest_conf(logger, user, password, radius_server_conf):
    if isinstance(radius_server_conf, RadiusConf):
        ok, msg = radius_server_conf.isValidWithMsg()
        if not ok:
            return False, msg
        #take only the first
        radius_server_conf = RadiusConf.servers[0]
    if not isinstance(radius_server_conf, RadiusServer):
        raise ValueError(
            "Only supported : RadiusConf, RadiusServer, "
            "but got %s instead" % type(radius_server_conf)
            )
    return radtest(
        logger,
        user,
        password,
        radius_server_conf.server_string(),
        radius_server_conf.secret,
        timeout=radius_server_conf.timeout,
    )

