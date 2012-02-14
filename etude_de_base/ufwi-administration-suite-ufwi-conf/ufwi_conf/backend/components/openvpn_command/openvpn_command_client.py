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


import re
from twisted.internet.protocol import Protocol, ReconnectingClientFactory
from twisted.internet import reactor

class VPNUser:
    def __init__(self, vpn_ip, cert_cn, connected_since):
        self.vpn_ip = vpn_ip
        self.cert_cn = cert_cn
        self.connected_since = connected_since

class OpenVPNCommandClient(Protocol):
    def __init__(self):
        self.re_activity = [
            re.compile('>LOG:[0-9]*,I,[0-9.]*:[0-9]* .* Peer Connection Initiated with [0-9.]*:[0-9]*'),
            re.compile('>LOG:[0-9]*,N,.*/[0-9.]*:[0-9]* Connection reset, restarting \[[0-9]*\]'),
            re.compile('>LOG:[0-9]*,I,.*/[0-9.]*:[0-9]* \[.*\] Inactivity timeout \(--ping-restart\), restarting')
            ]

        self.re_connected = [
            re.compile('([0-9.]*),(.*),[0-9.]*:[0-9]*,([^,]*)'),
            ]

# TCP/UDP connection
# LOG:1248858297,I,127.0.0.1:35019 [client2] Peer Connection Initiated with 127.0.0.1:35019

# TCP disconnection
# LOG:1248858273,N,client2/127.0.0.1:35010 Connection reset, restarting [0]

# UDP disconnection
# LOG:1248861135,I,client2/127.0.0.1:35326 [client2] Inactivity timeout (--ping-restart), restarting

# Connected users
# client2,127.0.0.1:49675,4067,5354,Wed Jul 29 13:59:18 2009

    def startCounting(self):
        if self.factory.refreshing:
            return
        self.transport.write('status\r\n')
        self.factory.refreshing = True
        self.factory.refreshed_count = 0
        self.factory.refreshed_client_lst = {}

    def dataReceived(self, data):
        # Initialization
        for line in data.splitlines():
            if line == ">INFO:OpenVPN Management Interface Version 1 -- type 'help' for more info":
                self.transport.write('verb 1\r\n')
                self.startCounting()
                self.transport.write('log on\r\n')

            # End of client list
            if line == "END":
                self.factory.count = self.factory.refreshed_count
                self.factory.client_lst = self.factory.refreshed_client_lst
                self.factory.refreshing = False

            # Check for a connection
            for rexp in self.re_activity:
                if rexp.match(line) is not None:
                    self.startCounting()

            # Check for a disconnection
            for rexp in self.re_connected:
                match = rexp.match(line)
                if match is not None:
                    user = VPNUser(match.group(1), match.group(2), match.group(3))
                    self.factory.refreshed_client_lst[match.group(1)] = user
                    self.factory.refreshed_count += 1

    def connectionMade(self):
        self.factory.resetDelay()

class OpenVPNClientFactory(ReconnectingClientFactory):
    protocol = OpenVPNCommandClient

    def __init__(self):
        self.count = 0
        self.refreshing = False
        self.client_lst = {}


    def disconnect(self):
        self.stopTrying()
        self.connector.disconnect()

    def getUserCount(self):
        return self.count

    def getClientList(self):
        return self.client_lst

def startOpenVPNClient(address, port):
    factory = OpenVPNClientFactory()
    factory.connector = reactor.connectTCP(address, port, factory)
    return factory


