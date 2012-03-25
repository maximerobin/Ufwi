
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

from os import kill, getcwd
from os.path import join
from signal import SIGINT
from subprocess import Popen
from time import time, sleep
import sys

from nucentral.client import NuCentralClientBase, NuCentralError
from .tool_conf import conf, conf_stop

username = "admin"
password = "adminsecret"
username2 = "haypo"
password2 = "hayposecret"

class ServerError(Exception):
    pass

class Server:
    def __init__(self):
        self.srcdir = getcwd()
        self.vardir = conf(
            self.srcdir,
            username, password, username2, password2)
        self.process = None
        self.timeout = 10.0
        self.status = None
        self.is_running = False
        self.start()

    def start(self):
        NUCENTRAL_TAC = [sys.executable,
            "-u", "/usr/bin/twistd",
            "-ny",
            join(self.srcdir, "nucentral.tac")]
        self.process = Popen(NUCENTRAL_TAC)
        self.is_running = True
        self.waitServer()

    def waitServer(self):
        timeout = time() + self.timeout
        while time() < timeout:
            if not self.isRunning():
                break
            try:
                client = createClient()
                client.authenticate(username, password)
                client.call("CORE", "getStatus")
                return
            except NuCentralError:
                sleep(0.5)
        raise ServerError("Unable to start NuCentral server!")

    def poll(self):
        if self.is_running:
            status = self.process.poll()
            if status is not None:
                self.is_running = False
                self.status = status
        return self.status

    def isRunning(self):
        if self.is_running:
            self.poll()
        return self.is_running

    def stop(self):
        if self.isRunning():
            kill(self.process.pid, SIGINT)
            self.process.wait()
            self.is_running = False
            self.process = None
        if self.vardir:
            conf_stop(self.vardir)
            self.vardir = None

    def __del__(self):
        self.stop()

def createServer():
    return Server()

def createClient():
    return NuCentralClientBase(protocol="http", host='127.0.0.1')

class NuCentralTest:
    server = None
    client = None
    AUTHENTICATE = True

    def setup_class(self):
        self.server = createServer()
        self.client = createClient()
        if self.AUTHENTICATE:
            self.client.authenticate(username, password)

    def teardown_class(self):
        self.client.logout()
        self.server.stop()

