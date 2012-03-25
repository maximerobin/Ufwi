# -*- coding: utf-8 -*-
"""
Copyright (C) 2009-2011 EdenWall Technologies
Written by Romain Bignon <romain AT inl.fr>

$Id$
"""

from ufwi_rpcd.client.base import RpcdClientBase
from twisted.internet.threads import deferToThread

def client_call_threaded(registration, method, *args):
    client = RpcdClientBase(registration.hostname, registration.port, registration.protocol, 'multisite.slave')
    client.authenticate(registration.username, registration.password)
    result = client.call(method, *args)
    client.logout()
    return result

class RegistrationClient:

    def __init__(self, username='', password='', hostname='',
                       port=0, protocol=''):
        self.username = str(username)
        self.password = str(password)
        self.hostname = str(hostname)
        self.port = int(port)
        self.protocol = str(protocol)

    def save(self):
        d = dict()
        d['username'] = self.username
        d['password'] = self.password
        d['hostname'] = self.hostname
        d['port'] = self.port
        d['protocol'] = self.protocol
        return d

    def call(self, method, *args):
        d = deferToThread(client_call_threaded, self, method, *args)
        return d
