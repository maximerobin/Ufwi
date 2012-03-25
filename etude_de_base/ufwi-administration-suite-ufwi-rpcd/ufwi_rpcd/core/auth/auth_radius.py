# -*- coding: utf-8 -*-

"""
Copyright (C) 2009-2011 EdenWall Technologies
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

from ufwi_rpcd.backend import tr, AuthError
from ufwi_rpcd.core.error import AUTH_RADIUS_ERROR

from .auth_basemethods import AbstractAuth

try:
    import pyrad.packet
    from pyrad.client import Client
    from pyrad.dictionary import Dictionary
    HAVE_RADIUS = True
except ImportError:
    HAVE_RADIUS = False

class AuthRadius(AbstractAuth):
    """
    Radius authentication
    """

    PARAMETERS = ['hostname', 'secret']

    def __init__(self,*args,**kwargs):
        AbstractAuth.__init__(self)

        if not HAVE_RADIUS:
            raise AuthError(AUTH_RADIUS_ERROR, "Radius support isn't activated")

        try:
            self.hostname = kwargs['hostname']
            self.secret = kwargs['secret']
        except KeyError, err:
            raise AuthError(AUTH_RADIUS_ERROR,
                            tr("Missing parameters to build Radius object: %s"),
                            err)

        # XXX do not hardcode these path
        self.srv = Client(server=self.hostname,
                          secret=self.secret,
                          dict=Dictionary("/etc/radiusclient/dictionary",
                                          "/etc/radiusclient/dictionary.merit",
                                          "/usr/share/freeradius/dictionary.rfc2865"))

    def authenticate(self, username, challenge):
        if AbstractAuth.authenticate(self, username, challenge):
            return True

        req = self.srv.CreateAuthPacket(code=pyrad.packet.AccessRequest,
                                        User_Name=unicode(username),
                                        NAS_Identifier='edenwall')

        req["User-Password"] = req.PwCrypt(unicode(challenge))
        reply = self.srv.SendPacket(req)

        return reply.code == pyrad.packet.AccessAccept

    def getGroups(self, username):
        return AbstractAuth.getGroups(self, username)

    def getAllGroups(self):
        return []

    def getStoragePaths(self):
        """
        storage is external
        """
        pass
