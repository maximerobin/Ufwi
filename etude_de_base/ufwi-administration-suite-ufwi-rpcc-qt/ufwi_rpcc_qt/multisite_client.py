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

$Id: ufwi_rpcd_client.py 13500 2009-10-15 13:13:28Z haypo $
"""

PROTOCOL_VERSION = '0.1'

DEFAULT_HOST = u"localhost"
DEFAULT_PROTOCOL = u"https"
DEFAULT_HTTP_PORT = 8080
DEFAULT_HTTPS_PORT = 8443
DEFAULT_PORT = DEFAULT_HTTPS_PORT
DEFAULT_CLIENT_NAME = 'ufwi_rpcd.client'
DEFAULT_STREAMING_PORT = 8080   # udp

# A client should call session.keepAlive() every KEEP_ALIVE_SECONDS seconds
KEEP_ALIVE_SECONDS = 60

class MultisiteClient:
    """
    Client for Rpcd server. Methods:

      - client.authenticate(login, password)
      - client.call('component', 'service', ...)
      - client.logout()

    """

    def __init__(self, host, client):
        #RpcdClient.__init__()
        self.host = host
        self.client = client
        self.login = client.login

    def __getattr__(self, name):
        if hasattr(self.client, name):
            print "return client's attr:", name
            return getattr(self.client, name)
        print "could not find attr", name

    def async(self, create=True):
        return self

    def unref(self, ignored):
        return

    def streaming(self):
        print "streaming"
        return
        ## Create the streaming object if a class is given to instance it.
        #if self._streaming:
        #    return self._streaming
        #if self._streaming_class:
        #    try:
        #        self._streaming = self._streaming_class(self)
        #        return self._streaming
        #    except Exception:
        #        # At first error, disable streaming
        #        # to avoid similar (duplicate) errors
        #        self._streaming_class = None
        #        raise
        #return None

    def call(self, *args, **kw):
        callback = None
        if 'callback' in kw.keys():
            callback = kw['callback']
            kw.pop('callback')
        ret = self.client.call('multisite_master', 'callRemote', self.host, *args)
        if callback is not None:
            callback()
        return ret

    def logout(self):
        print "loggout"
        return
        #self.debug("Logout")
        #if self._streaming:
        #    self._streaming.stop()
        #    self._streaming = None
        #if self._async:
        #    self._async.stop()
        #    self._async = None
        #if self.cookie:
        #    try:
        #        self.call('session', 'destroy')
        #    except RpcdError:
        #        pass
        #self._closeServer()
        #self.clearCookie()

