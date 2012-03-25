# -*- coding: utf-8 -*-
"""
Copyright (C) 2009-2011 EdenWall Technologies
Written by Romain Bignon <romain AT inl.fr>

$Id$
"""

import random
from threading import Lock
from time import mktime, gmtime

from twisted.internet.defer import succeed
from twisted.internet.threads import deferToThread
from ufwi_rpcd.backend.logger import Logger
from ufwi_rpcd.backend.error import RpcdError
from ufwi_rpcd.backend import tr
from ufwi_rpcd.client.base import RpcdClientBase

def client_create_threaded(request, username, password):

    request.mutex.acquire()
    try:
        request.client = RpcdClientBase(request.hostname, request.port, request.protocol, 'multisite.master')
        return request.client.authenticate(username, password)
    finally:
        request.mutex.release()

def client_call_threaded(request, method, *args):
    request.mutex.acquire()
    result = None
    try:
        if not request.client:
            raise RpcdError("There isn't any RpcdClientBase instance, during call %s %s" % (method, args))

        result = request.client.call(method, *args)
    finally:
        request.mutex.release()

    return result

def client_logout(request):
    try:
        request.mutex.acquire()
        if request.client is not None:
            request.client.logout()
    finally:
        request.client = None
        request.mutex.release()

class RequestFirewallJob(Logger):

    def __init__(self, core, name, hostname, port, protocol):
        Logger.__init__(self, "request_firewall_job")
        self.core = core
        self.name = name
        self.hostname = hostname
        self.port = port
        self.protocol = protocol
        self.client = None
        self.mutex = Lock()
        self.firewall = None

    def init_transaction(self, login, password):
        """
        Authenticate myself with the admin password on slave.
        """
        return deferToThread(client_create_threaded, self, login, password)

    def create_slave_account(self):
        """
        Create an account for slave. It is in the 'multisite' group.

        @return  username, password
        """
        while 1:
            # retry until username is taken.
            username = 'multisite_registration_%s_%d' % (self.name, random.randint(0,999999))
            password = '%d' % random.randint(0,999999)

            # TODO remove 'admin' from groups. It's a hack to allow firewall to call my services.
            # It is because it is currectly not possible to set group acls.
            if self.core.auth.addUser(username, 'SHA256', password, ['admin', 'multisite']):
                return username, password

    def remove_account(self, username):
        """
        Remove an account for slave.
        """
        return self.core.auth.delUser(username)

    def send_password(self, username, password):
        """
        Send password to slave and how to connect to me.
        """
        for protocol in ('https', 'http'):
            try:
                using_protocol = self.core.listening[protocol]
            except KeyError:
                pass
            else:
                return deferToThread(client_call_threaded, self, 'multisite_slave',
                                     'request_registration', self.name, using_protocol,
                                     protocol, username, password)

        self.error("Why don't I listen on any port?")
        raise RpcdError(tr("Does the master server listen on a port?"))

    def test_slave_state(self):
        return deferToThread(client_call_threaded, self, 'CORE', 'getComponentList')

    def haveCheckTime(self, slave_services):
        if 'checkTime' in slave_services:
            return deferToThread(client_call_threaded, self, 'multisite_slave', 'checkTime', mktime(gmtime()))
        return succeed(None)

    def test_slave_time(self):
        d = deferToThread(client_call_threaded, self, 'CORE', 'getServiceList', 'multisite_slave')
        d.addCallback(self.haveCheckTime)
        return d

    def logout(self):
        return deferToThread(client_logout, self)
