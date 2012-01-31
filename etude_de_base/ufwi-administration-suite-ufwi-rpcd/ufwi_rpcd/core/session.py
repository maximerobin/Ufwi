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

from base64 import b64encode, b32encode
from datetime import datetime, timedelta
from glob import glob
from os import unlink
from os.path import join as path_join, basename
import pickle
from M2Crypto.Rand import rand_bytes

from twisted.internet.defer import DeferredList

from ufwi_rpcd.common.tools import mkdirNew, timedelta2seconds
from ufwi_rpcd.common.error import RPCD_ERRORS
from ufwi_rpcd.common.monotonic_time import monotonic_time

from ufwi_rpcd.backend import tr, SessionError, AclError, AuthError
from ufwi_rpcd.backend.component import Component
from ufwi_rpcd.backend.cron import scheduleRepeat
from ufwi_rpcd.backend.error import exceptionAsUnicode
from ufwi_rpcd.backend.session_storage import SessionStorage

from ufwi_rpcd.core import events
# from ufwi_rpcd.core.audit import AuditEvent
from ufwi_rpcd.core.context import Context
from ufwi_rpcd.core.getter import getUnicode
from ufwi_rpcd.core.lock import PersistentLock
from ufwi_rpcd.core.version import PROTOCOL_VERSION
from ufwi_rpcd.core.error import (
    SESSION_INVALID_ARG, SESSION_INVALID_VERSION,
    SESSION_NO_USER, SESSION_DUPLICATE, SESSION_INVALID_COOKIE,
    SESSION_GEN_COOKIE_ERROR, SESSION_DIFFERENT_ADDRESS,
    ACL_PERMISSION_DENIED, AUTH_PERMISSION_DENIED)

# 128 bits of entropy
COOKIE_LENGTH = 16
COOKIE_BASE64_LENGTH = 24

class Session(SessionStorage):
    def __init__(self, cookie, filename, user):
        SessionStorage.__init__(self)
        self.cookie = cookie
        self.filename = filename
        self.user = user
        # Use monotonic_time() to ignore NTP time update
        # (seconds since an arbitrary starting point)
        self.creation = monotonic_time()
        self.last_access = self.creation
        # human readable timestamp
        self.creation_text = unicode(datetime.now())
        self.last_access_text = self.creation_text

    def getID(self):
        return self.cookie

    def getIdle(self):
        """
        idle time in as a datetime.timedelta object
        """
        idle = monotonic_time() - self.last_access
        return timedelta(seconds=idle)

    def update(self):
        if self.user.isAnonymous():
            # Don't update last_access for anonymous users
            return
        self.last_access = monotonic_time()
        self.last_access_text = unicode(datetime.now())


    @staticmethod
    def fromFilename(filename):
        input = open(filename, "rb")
        session = pickle.load(input)
        input.close()
        return session

    def _save(self):
        output = open(self.filename, "wb")
        pickle.dump(self, output, pickle.HIGHEST_PROTOCOL)
        output.close()

    def destroy(self, logger):
        events.emit('sessionDestroyed', self)
        try:
            unlink(self.filename)
        except OSError, err:
            logger.writeError(err)

    def dropRole(self, role):
        try:
            self.user.roles.remove(role)
            return True
        except KeyError:
            return False

    def exportXMLRPC(self, filter):
        idle_seconds = timedelta2seconds(self.getIdle())
        data = {
            'creation': self.creation_text,
            'last_access': self.last_access_text,
            'idle': idle_seconds,
        }
        if not filter:
            data['cookie'] = self.cookie
        user = self.user
        if user:
            user_data = {
                'host': user.host,
                'port': user.port,
                'client_name': user.client_name,
            }
            if user.client_release:
                user_data['client_release'] = user.client_release
            if user.login:
                user_data['login'] = user.login
            if not filter:
                user_data['groups'] = user.groups
                roles = list(user.roles)
                roles.sort()
                user_data['roles'] = roles
                user_data['protocol_version'] = user.protocol_version
            data['user'] = user_data
        return data

    def __repr__(self):
        return "<Session cookie=%r creation=%s last_access=%s user=%s>" % (
            self.cookie, self.creation_text, self.last_access_text, self.user)

    def __unicode__(self):
        return unicode(self.user)

class SessionManager(Component):
    """
    Manage user Rpcd sessions:

     - create a session with Rpcd authentication
     - dump the current session
     - destroy the current session
     - cleanup old sessions after N seconds (default: 1 hour)
    """

    NAME = "session"
    VERSION = "1.0"
    API_VERSION = 2
    # Most services are open by hardcoded permissions in ufwi_rpcd/core/acl.py
    ACLS = {
        'acl':  set(('getAcl',)),
   }

    def init(self, core):
        # Get max duration
        minutes = core.config.getint('CORE', 'max_session_duration')
        self.max_session_duration = timedelta(minutes=minutes)

        # Get the directory
        vardir = core.config.get('CORE', 'vardir')
        self.path = path_join(vardir, "sessions")
        mkdirNew(self.path)

        # Register the manager
        core.session_manager = self
        self.core = core
        # cookie => Session object
        self.sessions = {}

        # Remove old sessions each minute
        self.cleanup_task = scheduleRepeat(60, self.cleanup)

    def isOld(self, session):
        return (self.max_session_duration < session.getIdle())

    def destroy(self):
        self.cleanup_task.stop()

    def load(self):
        for filename in glob(path_join(self.path, "*.pickle")):
            try:
                self.loadSession(filename)
            except RPCD_ERRORS, err:
                self.writeError(err, "Unable to restore the session from the file %r" % basename(filename))
                # Remove the buggy session file
                try:
                    unlink(filename)
                except OSError:
                    pass
        if self.sessions:
            self.critical("%s session(s) recovered from disk" % len(self.sessions))

    def loadSession(self, filename):
        session = Session.fromFilename(filename)
        if self.isOld(session):
            session.destroy(self)
            return None
        if session.cookie in self.sessions:
            self.warning("Duplicate session on disk (cookie %r)" % session.cookie)
            return None
        self.sessions[session.cookie] = session

    def cleanup(self):
        try:
            delete = []
            for session in self.sessions.itervalues():
                if not self.isOld(session):
                    continue
                self.warning("Delete session %s (idle since %s)" % (
                    session, session.getIdle()))
                delete.append(session.cookie)
            for cookie in delete:
                session = self.sessions[cookie]
                session.destroy(self)
                del self.sessions[cookie]
        except Exception, err:
            self.writeError(err, "Unable to kill old sessions")

    def checkSession(self, context, session, user_session=None):
        if user_session is None:
            user_session = context.getSession()
        if user_session is session:
            # A user can see his own session
            return False
        if user_session.user.sameUser(session.user):
            # A user can see other sessions
            return False
        if context.hasRole('nucentral_admin'):
            # An admin can see and modify all sessions
            return False
        return True

    def service_list(self, context):
        "List of session cookies."
        user_session = context.getSession()
        for session in self.sessions.itervalues():
            filter = self.checkSession(context, session, user_session)
            yield session.exportXMLRPC(filter)

    def create(self, context, data):
        "Create an anonymous session"

        client_name = getUnicode("client_name", data['client_name'], 3, 100)
        protocol_version = getUnicode("protocol_version", data['protocol_version'], 3, 100)

        # Check client name and protocol version
        if not client_name or not (3 <= len(client_name) <= 20):
            raise SessionError(SESSION_INVALID_ARG,
                tr("Invalid client name: need a string with length in 3..20"))
        if not protocol_version or not (3 <= len(protocol_version) <= 10):
            raise SessionError(SESSION_INVALID_ARG,
                tr("Invalid protocol version: need a string with length in 3..10"))

        # Check protocol version
        if protocol_version != PROTOCOL_VERSION:
            raise SessionError(SESSION_INVALID_VERSION,
                tr("Invalid protocol version: %s"),
                repr(protocol_version))

        # Only a user with no session can create a new session
        if not context.user:
            raise SessionError(SESSION_NO_USER,
                tr("Only a user can create a session!"))
        if context.hasSession():
            raise SessionError(SESSION_DUPLICATE,
                tr("You already own a session!"))


        # Fill the user context
        user = context.user
        if 'client_release' in data:
            #size between 3 and 100
            user.client_release = getUnicode('client_release', data['client_release'], 3, 100)
        user.groups = ["anonymous"]
        user.client_name = client_name
        user.protocol_version = protocol_version

        # Create the session
        cookie = self.createCookie()
        filename = b32encode(cookie).strip("=") + ".pickle"
        filename = path_join(self.path, filename)
        cookie = b64encode(cookie)
        session = Session(cookie, filename, user)

        # Register the session and write it to the disk
        self.sessions[session.cookie] = session
        context.setSession(session)
        session.save()

        # Session created
        return session.cookie

    def authenticationSuccess(self, context):
        user = context.user
        if user.is_encrypted:
            transport = "an encrypted %s connection" % user.transport
        else:
            transport = "a clear text %s connection" % user.transport

        client =  'client %s proto %s' % (user.client_name, user.protocol_version)
        if user.client_release:
            client += ' release %s' % user.client_release

        self.warning(context, 'User "%s" connected from %s (%s:%s) (%s): authentication success'
            % (user.login, transport, user.host, user.port, client))
        context.getSession().save()
        return True

    def authenticationFailure(self, failure, context, login):
        # Log the authentiacation failure
        message = exceptionAsUnicode(failure)
        user = context.user
        self.error(context, u'Authentication failure from %s:%s (login "%s"): %s'
            % (user.host, user.port, login, message))
        return False

    def set_role(self, roles, user):
        user.roles = user.roles.union(role[2] for role in roles)

    def authenticate(self, valid_login, groups, context, login):
        if not valid_login:
            raise AuthError(AUTH_PERMISSION_DENIED,
                tr("Invalid login or password"))
        session = context.getSession()
        session.user.login = login
        user = session.user
        user.groups = groups
        context.user = user

        defers = []
        session_context = Context.fromComponent(self)
        for group in groups:
            defer = self.core.callService(session_context, "acl", "getAcl", group)
            defer.addCallback(self.set_role, user)
            defers.append(defer)
        defers = DeferredList(defers)
        defers.addCallback(lambda unused: self.authenticationSuccess(context))
        return defers

    def service_authenticate(self, context, login, password):
        "Authenticate current session with (login, password)."
        try:
            valid_login, groups = self.core.auth.login(context, login, password)
            return self.authenticate(valid_login, groups, context, login)
        except AuthError, err:
            return self.authenticationFailure(err, context, login)

    def getSession(self, context, cookie):
        try:
            return self.sessions[cookie]
        except KeyError:
            #event = AuditEvent.fromAuthFailure(context,
            #        u"EAS : Invalid session cookie %r" % (cookie,), cookie=cookie)
            #self.core.audit.emit(event)
            raise SessionError(SESSION_INVALID_COOKIE,
                tr("Invalid session cookie %s: expired session (timeout=%s)"),
                repr(cookie),
                str(self.max_session_duration))

    def getUserSession(self, context, cookie):
        user = context.user
        session = self.getSession(context, cookie)
        if session.user.host != user.host:
            raise SessionError(SESSION_DIFFERENT_ADDRESS,
                tr("The %s user can not use the  %s session: the source address is different.")
                % (unicode(user), unicode(session)))
        session.update()
        return session

    def createCookie(self):
        nb_try = 0
        while True:
            nb_try += 1
            if 1000 < nb_try:
                raise SessionError(SESSION_GEN_COOKIE_ERROR,
                    tr("Unable to generate a session cookie!"))
            cookie = rand_bytes(COOKIE_LENGTH)
            if cookie not in self.sessions:
                return cookie

    def service_dropRoles(self, context, roles):
        """
        Remove the specified roles from your session.
        Return the number of removed roles.

        Eg. session.dropRoles(('conf_read', 'conf_write'))
        """
        session = context.getSession()
        dropped = sum(int(session.dropRole(role)) for role in roles)
        session.save()
        return dropped

    def service_get(self, context):
        """
        Get the session as a dictionary, example: ::

            {'cookie': 'L+so0A3gos/ZTcMVQk2DzQ==',
             'creation': '2008-07-23 14:56:46.014210',
             'last_access': '2008-07-23 14:58:14.671649',
             'user': {'client_name': 'simple_client',
                      'groups': [],
                      'host': '127.0.0.1',
                      'login': 'a',
                      'port': 58174,
                      'protocol_version': '0.1'}}
        """
        session = context.getSession()
        return session.exportXMLRPC(False)

    def service_destroySession(self, context, cookie):
        """
        Destroy an arbitrary session using its cookie.
        You can destroy your own session or sessions of the same user.
        An administrator is allowed to destroy any session.
        """
        try:
            session = self.sessions[cookie]
        except KeyError:
            return False
        if self.checkSession(context, session):
            raise AclError(ACL_PERMISSION_DENIED,
                tr("You are not allowed to kill other users' sessions"))
        self.error(context, "User destroy session %s" % unicode(session))
        session.destroy(self)
        del self.sessions[cookie]
        return True

    def service_destroy(self, context):
        "Destroy current session."
        user = context.user
        cookie = context.getSession().cookie
        try:
            session = self.sessions[cookie]
        except KeyError:
            return False
        session.destroy(self)
        del self.sessions[cookie]
        self.warning(context, 'User "%s": connection closed' % unicode(user))
        return True

    def service_keepAlive(self, context):
        """
        Call this service every 5 minutes to make sure that your session does
        not expire.
        """
        return u"Born to be alive!"

    def checkServiceCall(self, context, service_name):
        if not context.hasSession():
            service = "%s.%s()" % (self.name, service_name)
            raise SessionError(tr("You need a session to call the %s service"), service)

    def formatServiceArguments(self, service, arguments):
        if service == 'authenticate':
            arguments = list(arguments)
            arguments[1] = '***'
        return Component.formatServiceArguments(self, service, arguments)

    def logService(self, context, logger, service, text):
        if service == 'keepAlive':
            # don't log calls to session.keepAlive()
            return
        Component.logService(self, context, logger, service, text)

    def fromFilename(self, filename):
        # Read the session cookie from the file
        fp = open(filename, "r")
        cookie = fp.read(COOKIE_BASE64_LENGTH)
        fp.close()

        # Get the session
        try:
            session = self.sessions[cookie]
        except KeyError:
            # Broken session: just remove the lock
            return None

        # Recreate the old lock
        key = basename(filename)
        return PersistentLock(key, session, filename)

