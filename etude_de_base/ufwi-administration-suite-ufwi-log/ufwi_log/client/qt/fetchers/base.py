# -*- coding: utf-8 -*-

"""
Copyright (C) 2008-2011 EdenWall Technologies
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

from PyQt4.QtCore import QObject, SIGNAL

class BaseFetcher(QObject):

    ERROR_SIGNAL = 'error(PyQt_PyObject)'
    NULOG_VERSION = 0

    def __init__(self, fragment, args, client):

        QObject.__init__(self)
        self.type = 'static'

        self.fragment = fragment
        self.args = args
        self.client = client

        if not BaseFetcher.NULOG_VERSION:
            BaseFetcher.NULOG_VERSION = self.client.call('CORE', 'getComponentVersion')

    def __del__(self):
        self.destructor()

    def destructor(self):
        pass

    def getArgs(self):
        return ()

    def isPrintable(self): return True

    def fetch(self, callback):
        raise NotImplementedError()

    def getTime(self, callback):
         module = 'ntp'
         self.asyncall(module, 'getServerTime', callback=callback, errback=self._errorHandler)

    def unref(self, callback):
        async = self.client.async(create=False)
        if async is None:
            return
        async.unref(callback)

    def call(self, component, service, *args):
        if self.fragment and self.fragment.firewall:
            return self.client.call('multisite_master', 'callRemote', self.fragment.firewall, component, service, *args)
        else:
            return self.client.call(component, service, *args)

    def asyncall(self, component, service, *args, **kwargs):
        if self.fragment and self.fragment.firewall:
            return self.client.async().call('multisite_master', 'callRemote', self.fragment.firewall, component, service, *args, **kwargs)
        else:
            return self.client.async().call(component, service, *args, **kwargs)

    def _errorHandler(self, e):
        self.emit(SIGNAL(self.ERROR_SIGNAL), e)


class GenericFetcher(BaseFetcher):
    def __init__(self, client):
        BaseFetcher.__init__(self, None, None, client)

