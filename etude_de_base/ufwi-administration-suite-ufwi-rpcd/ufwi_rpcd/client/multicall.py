# -*- coding: utf-8 -*-
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


from ufwi_rpcd.client import RpcdError
from ufwi_rpcd.common.transport import checkComplexType, TransportError
from ufwi_rpcd.common.error import exceptionAsUnicode
from xmlrpclib import MultiCall as rawMultiCall

class Multicall(object):
    def __init__(self, client):
        self.client = client
        self._calls = rawMultiCall(self.client.server)

    def addCall(self, *args):
        # Make sure that arguments are serializables
        try:
            checkComplexType(args)
        except TransportError, err:
            raise RpcdError("TransportError", exceptionAsUnicode(err))

        cookie = self.client.getCookie()
        self._calls.callService(cookie, *args)

    def __call__(self):
        results = []
        raw_results = self._calls().results
        for res in raw_results:
            failed = res[0]
            value = res[1]
            if failed:
                try:
                    self.client.processError(value)
                except Exception, e:
                    results.append(e)
            else:
                results.append(value)
        return results
