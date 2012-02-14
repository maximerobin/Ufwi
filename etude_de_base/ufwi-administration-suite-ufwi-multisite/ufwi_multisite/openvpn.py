# -*- coding: utf-8 -*-
"""
Copyright (C) 2009-2011 EdenWall Technologies
Written by Romain Bignon <romain AT inl.fr>

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
import os
from IPy import IP

from ufwi_rpcd.common.tools import mkdirNew
from ufwi_rpcd.common.process import createProcess, waitProcess
from ufwi_rpcd.backend.process import runCommandAsRoot
from ufwi_rpcd.backend.logger import Logger
from ufwi_rpcd.backend.error import RpcdError

class OpenVPNError(RpcdError):
    pass

class OpenVPNBase(Logger):

    def __init__(self, root_path, address, port, interface, key_file = None, cert_file = None, cacert_file = None, netmask=None):
        Logger.__init__(self, 'openvpn')

        self.root_path = root_path
        self.key_file = key_file
        self.cert_file = cert_file
        self.cacert_file = cacert_file

        self.DH1024_FILE = os.path.join(self.root_path, 'dh1024.pem')
        self.PID_FILE = os.path.join(self.root_path, 'openvpn.pid')
        self.CONFIG_FILE = os.path.join(self.root_path, 'openvpn.conf')

        if key_file is None:
            self.key_file = os.path.join(self.root_path, 'key.pem')
        if cert_file is None:
            self.cert_file = os.path.join(self.root_path, 'cert.pem')
        if cacert_file is None:
            self.cacert_file = os.path.join(self.root_path, 'cacert.pem')

        self.address = address
        self.port = port
        self.interface = interface

        if netmask:
            assert isinstance(netmask, IP)
            assert netmask.version() == 4
            assert netmask.prefixlen() < 32
            self.network = str(netmask.net())
            self.netmask = str(netmask.netmask())
        else:
            self.network = ''
            self.netmask = ''

        try:
            mkdirNew(self.root_path)
        except OSError:
            raise RpcdError('Unable to create directory: %s', self.root_path)

    def buildCertificates(self, key, cert, cacert):
        self.writeInFile(self.key_file, key)
        os.chmod(self.key_file, 0600)
        self.writeInFile(self.cert_file, cert)
        self.writeInFile(self.cacert_file, cacert)

    def setPort(self, port):
        self.port = port

    def getPort(self):
        return self.port

    def getAddress(self):
        return self.address

    def setAddress(self, address):
        self.address = address
        self.start()

    def writeInFile(self, filename, string):
        f = file(filename, 'w')
        f.write(string)
        f.close()

    def buildConfig(self):
        raise NotImplementedError()

    def writeConfig(self):
        config = self.buildConfig() % {'port':      self.getPort(),
                                       'address':   self.getAddress(),
                                       'ca':        self.cacert_file,
                                       'cert':      self.cert_file,
                                       'key':       self.key_file,
                                       'dh':        self.DH1024_FILE,
                                       'network':   self.network,
                                       'netmask':   self.netmask,
                                       'interface': self.interface,
                                      }

        self.writeInFile(self.CONFIG_FILE, config)


    def start(self):
        self.stop()
        self.writeConfig()

        p, code = runCommandAsRoot(self, ['/usr/sbin/openvpn',
                                          '--cd', self.root_path,
                                          '--config', self.CONFIG_FILE,
                                          '--writepid', self.PID_FILE])
        if code != 0:
            raise OpenVPNError('Unable to startup OpenVPN!')

        self.info('OpenVPN server started.')

    def __del__(self):
        self.stop()

    def isRunning(self):
        try:
            with open(self.PID_FILE) as f:
                return True
        except IOError:
            # It is not started
            return False

    def stop(self):
        try:
            with open(self.PID_FILE) as f:
                pid = f.readline().rstrip()
        except IOError:
            # It is not started
            return
        runCommandAsRoot(self, ['/bin/kill', '-9', pid])
        runCommandAsRoot(self, ['/bin/rm', self.PID_FILE])

        self.info('OpenVPN server stopped.')

class OpenVPNServer(OpenVPNBase):

    def buildConfig(self):
        try:
            file(self.DH1024_FILE)
        except IOError:
            with open(os.path.devnull, 'wb') as devnull:
                self.info('Generating a new DH Parameter key.')
                process = createProcess(self, ['/usr/bin/openssl', 'dhparam',
                                               '-out', self.DH1024_FILE,
                                               '1024'],
                                              stdout=devnull,
                                              stderr=devnull)
                if waitProcess(self, process, 60.0 * 10) != 0:
                    raise OpenVPNError('Unable to generate a DH Parameter key.')

        return """daemon
local %(address)s
port %(port)d
proto udp
dev %(interface)s
dev-type tun

ca %(ca)s
cert %(cert)s
key %(key)s
dh %(dh)s

server %(network)s %(netmask)s
ifconfig-pool-persist ipp.txt

keepalive 10 60

persist-key
comp-lzo
"""

class OpenVPNClient(OpenVPNBase):

    def buildConfig(self):
        return """daemon
client
remote %(address)s %(port)d
proto udp
dev %(interface)s
dev-type tun
nobind
resolv-retry infinite

ca %(ca)s
cert %(cert)s
key %(key)s

comp-lzo

persist-key
persist-tun

verb 3
"""

__all__ = ['OpenVPNServer', 'OpenVPNClient', 'OpenVPNError']
