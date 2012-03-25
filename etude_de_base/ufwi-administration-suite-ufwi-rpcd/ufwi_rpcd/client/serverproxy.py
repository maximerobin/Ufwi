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

from xmlrpclib import ServerProxy

class RpcdServerProxy(ServerProxy):
    def __init__(self, logger, url, ssl_config):
        keywords = {}
        if url.startswith('https'):
            # Choose the right SSL Transport (depend on xmlrpclib version)
            import xmlrpclib
            if hasattr(xmlrpclib, 'GzipDecodedResponse'):
                # XML-RPC backport enabled: use our SSL transport, compatible
                # with the new XML-RPC library API
                from ufwi_rpcd.common.ssl.transport import SSL_Transport
            else:
                from M2Crypto.m2xmlrpclib import SSL_Transport

            # Use M2Crypto transport
            context = ssl_config.createContext(logger)
            keywords['transport'] = SSL_Transport(context)

        else:
            logger.critical("WARNING: Unsafe cleartext connection (HTTP)")

        ServerProxy.__init__(self, url, **keywords)

