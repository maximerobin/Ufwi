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
import weakref
from ufwi_rpcd.common import EDENWALL
from ufwi_rpcd.backend import tr, SessionError
from ufwi_rpcd.core.error import SESSION_BROKEN_REF
from M2Crypto.SSL.TwistedProtocolWrapper import TLSProtocolWrapper
from M2Crypto.m2 import ssl_get_current_cipher, ssl_get_version
from M2Crypto.SSL.Cipher import Cipher

class UserContext:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.is_secure = None
        self.login = None
        self.groups = []
        self.roles = set()
        self.client_name = None
        self.protocol_version = None
        self.is_encrypted = None
        self.transport = None
        self.client_release = None

    def readRequest(self, request):
        if request.isSecure():
            # PyOpenSSL (HTTPS) connection
            self.is_encrypted = True
            self.transport = u"HTTPS"
            return
        transport = request.channel.transport
        if isinstance(transport, TLSProtocolWrapper):
            # M2Crypto (HTTPS) connection
            self.is_encrypted = True
            ssl = transport.ssl.ssl
            proto = ssl_get_version(ssl)
            cipher = ssl_get_current_cipher(ssl)
            if cipher is not None:
                cipher = str(Cipher(cipher))
            else:
                cipher = 'HTTPS'
            self.transport = u"%s:%s" % (proto, str(cipher))
        else:
            # Clear text (HTTP) connection
            self.is_encrypted = False
            self.transport = u"HTTP"

    def __repr__(self):
        info = ["host=%s port=%s" % (self.host, self.port)]
        if self.client_name:
            info.append("client_name=%r" % self.client_name)
        if self.client_release:
            info.append("client_release=%r" % self.client_release)
        if self.protocol_version:
            info.append("protocol_version=%s" % self.protocol_version)
        if self.login:
            info.append("login=%r" % self.login)
        if self.groups:
            info.append("groups=%r" % self.groups)
        if self.roles:
            info.append("roles=%r" % list(self.roles)) # prevent displaying "set([])"
        return "<UserContext %s>" % ' '.join(info)

    def __unicode__(self):
        text =  "%s:%s" % (self.host, self.port)
        if self.login:
            text = "%s@" % self.login + text
        return text

    def isAnonymous(self):
        return (self.login is None)

    def sameUser(self, user):
        if self.isAnonymous() or user.isAnonymous():
            # Anonymous user never match other users
            return False
        return (self.login == user.login)

class ComponentContext:
    def __init__(self, name, acls):
        self.name = name
        self.acls = acls

    def __repr__(self):
        return "<ComponentContext name=%s>" % self.name

    def __unicode__(self):
        return self.name

class Context:
    def __init__(self, user=None, component=None):
        if (not user) and (not component):
            raise SessionError(
                tr("A context requires a user or component session"))
        # UserContext object (or None)
        self.user = user
        # ComponentContext object (or None)
        self.component = component
        # pointer to a Session or SessionStorage
        self._session_ref = None

    def setSession(self, session):
        self._session_ref = weakref.ref(session)
        if hasattr(session, 'user'):
            self.user = session.user

    def readSession(self, core, cookie):
        session = core.session_manager.getUserSession(self, cookie)
        if session:
            self.setSession(session)

    def getSession(self):
        if self._session_ref is None:
            return None
        session = self._session_ref()
        if not session:
            raise SessionError(SESSION_BROKEN_REF,
                tr("Context: broken reference to the session!"
                   " (session killed?)"))
        return session

    def isUserContext(self):
        return self.user != None

    def isAuthenticatedUser(self):
        return (self.user != None) and bool(self.user.login)

    def isComponentContext(self):
        return self.component != None

    def isAnonymous(self):
        if self.user:
            return self.user.isAnonymous()
        else:
            # Components are not anonymous
            return False

    def hasSession(self):
        return (self.getSession() is not None)

    if EDENWALL:
        def hasRole(self, role):
            if self.user:
                return (role in self.user.roles)
            else:
                # Components have no role
                return False
    else:
        def hasRole(self, role):
            if self.user:
                return True
            else:
                # Components have no role
                return False

    @staticmethod
    def fromClient(request):
        client = request.client
        user_context = UserContext(client.host, client.port)
        user_context.readRequest(request)
        return Context(user=user_context)

    @staticmethod
    def fromComponent(component):
        component_context = ComponentContext(component.name, component.getAcls())
        ctx = Context(component=component_context)
        ctx.setSession(component.session)
        return ctx

    def __unicode__(self):
        if self.user:
            return unicode(self.user)
        else:
            return u"<%s component>" % unicode(self.component)

    def __repr__(self):
        info = []
        if self.user:
            info.append('user=%r' % self.user)
        if self.component:
            info.append('component=%r' % self.component)
        session = self.getSession()
        if session:
            info.append('session=%r' % session)
        return "<Context %s>" % ' '.join(info)

    def ownerString(self):
        if self.isUserContext():
            return self.user.login
        else:
            return self.component.name
