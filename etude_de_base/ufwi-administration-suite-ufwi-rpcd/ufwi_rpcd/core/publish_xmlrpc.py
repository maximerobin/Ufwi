"""
Copyright (C) 2007-2011 EdenWall Technologies
Written by Pierre Chifflier <p.chifflier AT inl.fr>

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

from twisted.web.xmlrpc import XMLRPC, Fault
import xmlrpclib
from twisted.internet import defer
from twisted.web import server
from ufwi_rpcd.core.base_service import BaseService
from ufwi_rpcd.core.version import VERSION

class RPCPublisher(XMLRPC, BaseService):
    """ XXX check that request.getClientIP() is really the _peer_ IP """

    def __init__(self, core):
        XMLRPC.__init__(self)
        BaseService.__init__(self, core)
        self.putSubHandler('system', self)

    def xmlrpc_callService(self, *args, **kwargs):
        return self.callService(*args, **kwargs)

    def xmlrpc_multicall(self, *args, **kwargs):
        multicall_res = []
        calls = args[0][0]
        for call in calls:
            fct = self._getFunction(call['methodName'])
            res = fct(call['params'], args[1])
            if isinstance(res, defer.Deferred):
                multicall_res.append(res.result)
            else:
                multicall_res.append(res)
        return multicall_res

    def xmlrpc_version(self, *args, **kwargs):
        return VERSION

    def render(self, request):
        # Copy/paste from twisted/web/xmlrpc.py, Resource.render_POST() method
        request.content.seek(0, 0)
        request.setHeader("content-type", "text/xml")
        try:
            args, functionPath = xmlrpclib.loads(request.content.read())
        except Exception, e:
            f = Fault(self.FAILURE, "Can't deserialize input: %s" % (e,))
            self._cbRender(f, request)
        else:
            try:
                function = self._getFunction(functionPath)
            except Fault, f:
                self._cbRender(f, request)
            else:
                try:
                    args = self.getFunctionArguments(args, request)
                except Exception, e:
                    self._cbRender(self.serviceError(e, None, '', '', False), request)
                else:
                    defer.maybeDeferred(function, *args).addErrback(
                        self._ebRender
                    ).addCallback(
                        self._cbRender, request
                    )
        return server.NOT_DONE_YET

    def getFunctionArguments(self, args, request):
        """
        Get arguments given to xmlrpc functions.
        """

        return args, request
