# -*- coding: utf-8 -*-
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

from sys import exc_info
from twisted.python.failure import Failure
from twisted.internet.defer import FirstError

from ufwi_rpcd.common.error import formatTraceback
from ufwi_rpcd.common.transport import checkComplexType, TransportError

from ufwi_rpcd.backend import tr, ComponentError
from ufwi_rpcd.backend.error import (exceptionAsUnicode,
    UnicodeException, CoreError)
from ufwi_rpcd.backend.logger import Logger

from ufwi_rpcd.core.context import Context
from ufwi_rpcd.core.session import SessionError, COOKIE_BASE64_LENGTH
from ufwi_rpcd.core.getter import getUnicode
from ufwi_rpcd.core.error import CORE_CALL_SERVICE_ERROR

class BaseService(Logger):
    def __init__(self, core):
        Logger.__init__(self, "service", parent=core)
        self.core = core

    def displayError(self, err, traceback, context,
    component_name=None, service_name=None):
        if component_name:
            try:
                logger = self.core._getComponent(component_name)
            except ComponentError:
                logger = self
        else:
            logger = self
        if context.component:
            who = u" called by %s" % unicode(context.component)
        else:
            # Already displayed by the context
            who = u''
        if component_name and service_name:
            title = u"Error in the service %s.%s()%s" % (component_name, service_name, who)
        else:
            title = u"Error in a service%s" % who
        logger.writeError(context, err, title, traceback=traceback)

    def extractError(self, err):
        traceback = None
        if isinstance(err, Failure):
            traceback = err.getBriefTraceback()
            err = err.value
        if isinstance(err, FirstError):
            err = err.subFailure.value
        if traceback is None:
            traceback = exc_info()
        return (err, traceback)

    def encodeError(self, context, err, traceback):
        info = {'type': err.__class__.__name__}
        if isinstance(err, UnicodeException):
            info['format'] = err.format
            info['application'] = err.application
            info['component'] = err.component
            info['error_code'] = err.error_code
            if err.format_arguments:
                info['arguments'] = err.format_arguments
            if err.additionals:
                info['additional'] = err.additionals
        else:
            info['message'] = exceptionAsUnicode(err, add_type=False)
        if traceback and context and context.hasRole("nucentral_debug"):
            info['traceback'] = formatTraceback(traceback)
        return info

    def serviceError(self, err, context, component_name, service_name, display=True):
        err, traceback = self.extractError(err)
        if display:
            self.displayError(err, traceback, context, component_name, service_name)
        info = self.encodeError(context, err, traceback)
        return (True, info)

    def formatResult(self, result, service):
        try:
            checkComplexType(result)
        except TransportError, err:
            raise TransportError("%s (result of the %s service ())" % (err, service))
        return (False, result)

    def callService(self, args, request):
        context = Context.fromClient(request)
        component_name = None
        service_name = None
        try:
            # Read the arguments
            if len(args) < 3:
                raise CoreError(CORE_CALL_SERVICE_ERROR,
                    tr("callService(cookie, component, service, *args)"
                       " requires at least 3 parameters"))
            cookie, component_name, service_name = args[:3]
            args = args[3:]

            # Validate arguments
            cookie = getUnicode("cookie", cookie, 0, COOKIE_BASE64_LENGTH)
            component_name = getUnicode("component", component_name, 1, 100)
            service_name = getUnicode("service", service_name, 1, 100)

            return self._callService(context, cookie, component_name, service_name, args)
        except SessionError, err:
            self.core.critical("Session error from %s: %s" % (unicode(context.user), exceptionAsUnicode(err)))
            return self.serviceError(err, context, component_name, service_name, display=False)
        except Exception, err:
            return self.serviceError(err, context, component_name, service_name)

    def _callService(self, context, cookie, component_name, service_name, args):
        service = '%s.%s' % (component_name, service_name)

        # Read the session using the cookie
        if cookie:
            context.readSession(self.core, cookie)

        # Create a defered to execute the request
        defer = self.core.callService(context, component_name, service_name, *args)
        defer.addCallback(self.formatResult, service=service)
        defer.addErrback(self.serviceError, context, component_name, service_name)
        return defer

