"""
M2Crypto transport for xmlrpclib version Python 2.6+.


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


from M2Crypto import version
from xmlrpclib import Transport
from M2Crypto.httpslib import HTTPSConnection
from urllib import splituser, splitport

class SSL_Transport(Transport):
    """
    SSL Transport for HTTPS/1.1 (keep-alive)
    """
    user_agent = "M2Crypto/%s" % version

    def __init__(self, ssl_context, *args, **kw):
        Transport.__init__(self, *args, **kw)
        self.ssl_ctx = ssl_context
        # Connection cache: (url, HTTPSConnection object)
        self._connection = (None, None)

    def make_connection(self, url):
        # If the url is the same, reuse the previous connection
        if self._connection and url == self._connection[0]:
            return self._connection[1]

        # Open a new connection
        user_passwd, host_port = splituser(url)
        host, port = splitport(host_port)
        if port is not None:
            port = int(port)
        self._connection = url, HTTPSConnection(host, port=port, ssl_context=self.ssl_ctx)
        return self._connection[1]

