#coding: utf-8
"""
Copyright (C) 2007-2011 EdenWall Technologies
Written by Pierre Chifflier <p.chifflier AT edenwall.com>
           Pierre-Louis Bonicoli <bonicoli AT edenwall.com>

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

from __future__ import with_statement

from os import getenv
from os.path import realpath
from time import localtime, strftime, time
from datetime import datetime
from xmlrpclib import Error as XMLRPCError
from errno import ECONNREFUSED
import socket

from M2Crypto.SSL import SSLError

from ufwi_rpcd.common.transport import checkComplexType, TransportError
from ufwi_rpcd.common.error import exceptionAsUnicode, reraise, formatError
from ufwi_rpcd.common.logger import Logger
from ufwi_rpcd.common.human import humanRepr, fuzzyTimedelta
from ufwi_rpcd.common.services import HIDE_SERVICE_RESULT

from ufwi_rpcd.common import tr
from ufwi_rpcd.client import RpcdError, SessionError
from ufwi_rpcd.client.ssl_config import ClientSSLConfig
from ufwi_rpcd.client.serverproxy import RpcdServerProxy

MAX_CALL_LENGTH = 300
MAX_RESULT_LENGTH = 100

PROTOCOL_VERSION = '0.1'

DEFAULT_HOST = u"192.168.1.1"
DEFAULT_PROTOCOL = u"https"
DEFAULT_HTTP_PORT = 8080
DEFAULT_HTTPS_PORT = 8443
DEFAULT_PORT = DEFAULT_HTTPS_PORT
DEFAULT_CLIENT_NAME = 'ufwi_rpcd.client'

# A client should call session.keepAlive() every KEEP_ALIVE_SECONDS seconds
KEEP_ALIVE_SECONDS = 60

HIDE_SERVICE_ARGUMENTS = {
    # Hide cookie
    'session.destroySession': (0,),

    # Hide passwords (and hash types)
    'session.authenticate': (1,),
    'auth.addUser': (1, 2),
    'auth.editUser': (1, 2),

    # Hide config (contain clear text password)
    'ufwi_ruleset.setConfig': (0,),
    'nulog.setConfig': (0,),
    'console_access.setConsoleAccessConfig': (0,),
}

class Cookie:
    def __init__(self, key):
        self.key = key
        self.refcount = 1

    def incref(self):
        self.refcount += 1

    def decref(self):
        self.refcount = max(self.refcount - 1, 0)
        return self.refcount

    def destroy(self):
        # Client got a SessionError: the cookie has been destroyed at server
        # side (timeout or destroyed by an administrator)
        self.key = ''
        self.refcount = 0

class RpcdClientBase(Logger):
    """
    Client for Rpcd server. Methods:

      - client.authenticate(login, password)
      - client.call('component', 'service', ...)
      - client.logout()

    The cookie can be shared between different clients
    """
    def __init__(self,
    host=None,
    port=None,
    protocol=None,
    client_name=None,
    ssl_config=None,
    cookie=None,
    client_release=None,
    logger_name=None):
        if not logger_name:
            logger_name = "client"
        Logger.__init__(self, logger_name)
        self.server = None
        self.login = None
        self._nb_call = 0
        self.recording = False
        self.recorded_calls = []
        # Cookie object
        if cookie:
            cookie.incref()
            self._cookie = cookie
        else:
            self._cookie = None
        self.client_release = client_release
        if not host:
            host = DEFAULT_HOST
        if not protocol:
            protocol = DEFAULT_PROTOCOL
        if port is None:
            if protocol == 'https':
                port = DEFAULT_HTTPS_PORT
            else:
                port = DEFAULT_HTTP_PORT
        if client_name:
            self.client_name = client_name
        else:
            self.client_name = DEFAULT_CLIENT_NAME

        # Record calls?
        filename = getenv('RPCD_RECORD_CALLS')
        if filename:
            self.record_filename = realpath(filename)
            self.error("Recording calls into %s" % self.record_filename)
            self.recording = True

        # Create transport server and set call service method
        self.protocol = protocol
        self.host = host
        self.port = port
        self.url = u"%s://%s:%s/RPC2" % (self.protocol, host, self.port)

        if ssl_config:
            self.ssl_config = ssl_config
        else:
            self.ssl_config = ClientSSLConfig()
        self.server = self._build_server_proxy()

        # Create a session
        self._createSession()

    def setRecordFilename(self, filename):
        self.record_filename = filename

    def setRecordingEnabled(self, enabled):
        if enabled:
            self.recording = True
        else:
            self.recording = False

    def _socketError(self, err):
        errno = err.args[0]
        if errno == ECONNREFUSED:
            text = tr("Connection refused to %s!\nIs the Rpcd server running and listening on port %s?") \
                % (self.url, self.port)
        else:
            text = tr("Unable to connect to %s: %s (error #%s)") \
                % (self.url, exceptionAsUnicode(err), errno)
        return RpcdError('socket.error', text)

    def formatService(self, component, service, args):
        key = "%s.%s" % (component, service)
        if key in HIDE_SERVICE_ARGUMENTS:
            args = list(args)
            for index in HIDE_SERVICE_ARGUMENTS[key]:
                if len(args) <= index:
                    # Missing argument: ignore the error
                    continue
                args[index] = '***'
            args = tuple(args)
        return "%s%s" % (key, humanRepr(args, MAX_CALL_LENGTH))

    def formatResult(self, component, service, result):
        key = "%s.%s" % (component, service)
        if key in HIDE_SERVICE_RESULT:
            return '***'
        is_error, data = result
        if is_error:
            return "(ERROR) %s" % humanRepr(data, MAX_RESULT_LENGTH)
        else:
            return "(success) %s" % humanRepr(data, MAX_RESULT_LENGTH)

    def getCookie(self):
        if (self._cookie is not None) and (not self._cookie.key):
            # the cookie has been destroyed in another thread
            self._cookie = None
        if self._cookie is None:
            raise SessionError(tr("User session has terminated. Please restart the application to create a new session."))
        return self._cookie.key

    def call(self, *args):
        cookie = self.getCookie()
        return self._call(cookie, *args)

    def _call(self, cookie, *args):
        # Make sure that arguments are serializables
        try:
            checkComplexType(args)
        except TransportError, err:
            raise RpcdError("TransportError", exceptionAsUnicode(err))

        # Check argument count
        if len(args) < 2:
            raise RpcdError("ClientError", tr("call() requires at least 2 arguments (component, service)"))
        service = self.formatService(args[0], args[1], args[2:])

        log = not (args[0] == 'session' and args[1] == 'keepAlive')

        # Send request throw transport server
        try:
            self._nb_call += 1
            call_number = self._nb_call
            if log:
                self.debug("Call #%s: %s" % (call_number, service))
            before = datetime.now()
            self.record_call(args, time_=before)
            result = self.server.callService(cookie,  *args)
            after = datetime.now()
            diff = fuzzyTimedelta(after - before)
            text = self.formatResult(args[0], args[1], result)
            if log:
                self.debug("Call #%s: %s -> %s (%s)" % (call_number, service, text, diff))
        except socket.error, err:
            raise self._socketError(err)
        except XMLRPCError, err:
            msg = tr("XML-RPC error on calling %s: %s") % (service, exceptionAsUnicode(err))
            raise RpcdError('xmlrpclib.Fault', msg)

        # Read value in result
        value = result[1]

        # Is it an error?
        if result[0]:
            self.processError(value)
        else:
            return value

    def record_call(self, args, time_=None):
        if not self.recording:
            return
        if not time_:
            time_ = datetime.now()
        timestamp = time_.strftime('%Y-%m-%d %H:%M:%S')
        self.recorded_calls.append((timestamp, args))

    def processError(self, value):
        # Text
        err_type = value['type']
        if 'format' in value:
            format = value['format']
            format = tr(format)
            if 'arguments' in value:
                arguments = value['arguments']
                if isinstance(arguments, list):
                    arguments = tuple(arguments)
                message = format % arguments
            else:
                message = format
        else:
            message = value['message']
            message = unicode(message)

        # Error code
        application = value.get('application')
        component = value.get('component')
        error_code = value.get('error_code')
        err_id = (application, component, error_code)
        if application:
            code = "%02u%02u%03u" % err_id
            code = tr("Error #%s") % code
            message = "%s: %s" % (code, message)

        # Additional errors
        if 'additionals' in value and len(value['additionals']) > 0:
            additionals = value['additionals']
            if 1 < len(additionals):
                message += u"\n\n" + u'\n - '.join(['Additional errors:'] + additionals)
            elif 1 == len(additionals):
                message += u"\n\n" + u'Additional error: %s' % additionals[0]

        # Raise the error
        traceback = value.get('traceback')
        if self._cookie and err_type == 'SessionError':
            self._cookie.destroy()
            self._cookie = None
            raise SessionError(message, traceback=traceback)
        else:
            raise RpcdError(err_type, message, traceback=traceback, err_id=err_id)

    def _createSession(self):
        if self._cookie is not None:
            # We have already a session: nothing to do
            return
        session_args = {
            'client_name': self.client_name,
            'protocol_version': PROTOCOL_VERSION
        }
        if self.client_release:
            session_args['client_release'] = self.client_release

        try:
            server_version, key = self._call('', 'CORE', 'createSession',
                session_args)
        except RpcdError:
            # Backwards compatibility (older servers don't have createSession)
            server_version, key = self._call('', 'CORE', 'clientHello',
                self.client_name, PROTOCOL_VERSION)

        if server_version != PROTOCOL_VERSION:
            raise RpcdError('protocol',
                tr("The server version (%s) is different from the client version (%s)!")
                % (server_version, PROTOCOL_VERSION))

        # Create the cookie (refcount=1)
        self._cookie = Cookie(key)

    def _closeServer(self):
        if self.server is None:
            return
        self.debug("Close the connexion to the server")
        try:
            self.server('close')
        except XMLRPCError:
            pass
        self.server = None

    def logout(self):
        if self._cookie is not None:
            refcount = self._cookie.decref()
            if not refcount:
                self.debug("Destroy session")
                try:
                    self.call('session', 'destroy')
                except (Exception, KeyboardInterrupt), err:
                    self.debug("Error on destroying the session: %s" % formatError(err))
            else:
                # the cookie is still used by another client
                self.debug("Don't destroy the session (refcount=%s)" % refcount)
            self._cookie = None
        self._closeServer()
        if self.recorded_calls:
            try:
                with open(self.record_filename, 'w') as fd:
                    print >>fd, '# coding: utf8'
                    print >>fd, 'recorded_calls = ('
                    for call in self.recorded_calls:
                        print >>fd, '    %s,' % repr(call)
                    print >>fd, ')'
                self.error("Recorded calls written into %s" % self.record_filename)
            except Exception, err:
                self.error("Could not write recorded calls to %r: %s"
                    % (self.record_filename, exceptionAsUnicode(err)))
            del self.recorded_calls[:]

    def authenticate(self, login, password):
        """
        Authenticate with specified login and password.
        Recreate a new session if session has expired.
        """
        self._createSession()
        ok = self.call('session', 'authenticate', login, password)
        if not ok:
            raise RpcdError("AuthError",
                "Invalid login or password")
        self.login = login

    def __del__(self):
        self.logout()

    def _build_server_proxy(self):
        self.info("Connecting to %s..." % self.url)
        before = datetime.now()
        try:
            # ServerProxy() doesn't support unicode URI:
            # http://bugs.python.org/issue7093
            #
            # M2Crypto.SSL_Transport() doesn't support unicode URI:
            # bio.send(unicode) adds nul bytes padding. See also:
            # https://bugzilla.osafoundation.org/show_bug.cgi?id=12931
            url = str(self.url)
            server = RpcdServerProxy(self, url, self.ssl_config)
            # pre-flight check: call version() method
            server.version()
        except SSLError, err:
            msg = tr("The connection was rejected during the SSL handshake, check your SSL configuration.")
            reraise(RpcdError('SSL', msg))
        except socket.error, err:
            reraise(self._socketError(err))
        except XMLRPCError, err:
            msg = tr("XML-RPC error on getting server version: %s") % exceptionAsUnicode(err)
            reraise(RpcdError('xmlrpclib.Fault', msg))
        except Exception, err:
            reraise(RpcdError('protocol',
                tr('Unable to connect to "%s": %s') % (self.url, exceptionAsUnicode(err))))
        after = datetime.now()
        diff = fuzzyTimedelta(after - before)
        self.warning("Connected to %s (%s)" % (self.url, diff))
        return server

    def clone(self, logger_name):
        # Create a new client which can be used in a different thread (XML-RPC
        # library is not thread safe).
        #
        # Share the cookie with the new client: cookie reference counter will
        # be incremented. The session is destroyed when the last client calls
        # logout().
        return RpcdClientBase(
            host=self.host,
            port=self.port,
            protocol=self.protocol,
            client_name=self.client_name,
            ssl_config=self.ssl_config,
            cookie=self._cookie,
            logger_name=logger_name)

