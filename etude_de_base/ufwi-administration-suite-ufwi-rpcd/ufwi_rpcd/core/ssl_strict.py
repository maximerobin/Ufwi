# -*- coding: utf-8 -*-
"""
Copyright (C) 2007-2011 EdenWall Technologies
Written by Pierre Chifflier <chifflier AT inl.fr>

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

from twisted.internet.ssl import DefaultOpenSSLContextFactory
from twisted.internet.ssl import ClientContextFactory
from OpenSSL.SSL import SSLv23_METHOD, VERIFY_PEER, VERIFY_FAIL_IF_NO_PEER_CERT, Context as SSL_Context

try:
    # Get C binding version
    from OpenSSL.crypto import X509_verify_cert_error_string
except ImportError:
    try:
        # ctypes binding version
        from ctypes import cdll, c_long, c_char_p
        from ctypes.util import find_library

        _libssl = cdll.LoadLibrary(find_library('ssl'))

        X509_verify_cert_error_string = _libssl.X509_verify_cert_error_string
        X509_verify_cert_error_string.restype = c_char_p
        X509_verify_cert_error_string.argtypes = (c_long,)
    except (ImportError, AttributeError):
        # ctypes module or X509_verify_cert_error_string symbol is missing:
        # use dummy fallback
        def X509_verify_cert_error_string(errnum):
            return str(errnum)

class StrictOpenSSLContextFactory(DefaultOpenSSLContextFactory):
    """Custom factory, supporting certificate chains.

    A certificate chain is composed of the server (or client certificate), followed
    by all certificates leading to the CA
    """
    def __init__(self, privateKeyFileName, certificateFileName,
             sslmethod=SSLv23_METHOD, certificateChainFile=None,
             verifyCallback=None):
        self.privateKeyFileName = privateKeyFileName
        self.certificateFileName = certificateFileName
        self.certificateChainFile = certificateChainFile
        self.verifyCallback       = (verifyCallback, )

        DefaultOpenSSLContextFactory.__init__(self,
                privateKeyFileName,
                certificateFileName,
                sslmethod=sslmethod)

    def verifyCertificate(self, conn, cert, errno, depth, retcode):
        cb = self.verifyCallback[0]
        if cb: return cb(cert)
        return retcode

    def _verify(self, connection, x509, errnum, errdepth, ok):
        """ This function will be called once for each certificate in the chain
        """
        #print '_verify (ok=%d):' % ok
        #print '  subject:', x509.get_subject()
        #print '  issuer:', x509.get_issuer()
        #print '  expired:', x509.has_expired()
        #print '  error %s at depth %s lookup: %s' % (
        #    errnum, errdepth, X509_verify_cert_error_string(errnum))
        return ok

    def getContext(self):
        """Create an SSL context.

        This is a sample implementation that loads a certificate from a file
        called 'server.pem'."""
        ctx = SSL_Context(SSLv23_METHOD)
        ctx.use_certificate_file(self.certificateFileName)
        ctx.use_privatekey_file(self.privateKeyFileName)
        ctx.load_client_ca(self.certificateChainFile)
        ctx.load_verify_locations(self.certificateChainFile)
        ctx.set_verify(VERIFY_PEER|VERIFY_FAIL_IF_NO_PEER_CERT,
                self._verify)
        ctx.set_verify_depth(10)
        return ctx



    def cacheContext(self):
        DefaultOpenSSLContextFactory.cacheContext(self)

        # Call a callback if defined to check certificate authentificity.
        if self.verifyCallback[0]:
            self._context.set_verify(VERIFY_PEER, self.verifyCertificate)

        if self.certificateChainFile != None:
            self._context.use_certificate_chain_file(self.certificateChainFile)

class StrictOpenSSLClientContextFactory(ClientContextFactory):

    def _verify(self, connection, x509, errnum, errdepth, ok):
        """ This function will be called once for each certificate in the chain
        """
        #print '_verify (ok=%d):' % ok
        #print '  subject:', x509.get_subject()
        #print '  issuer:', x509.get_issuer()
        #print '  expired:', x509.has_expired()
        #print '  error %s at depth %s lookup: %s' % (
        #    errnum, errdepth, X509_verify_cert_error_string(errnum))
        return ok

    def getContext(self):
        """Create an SSL context.

        This is a sample implementation that loads a certificate from a file
        called 'client.pem'."""
        ctx = ClientContextFactory.getContext(self)
        ctx.use_certificate_file(self.certificateFileName)
        ctx.use_privatekey_file(self.privateKeyFileName)
        ctx.load_client_ca(self.certificateChainFile)
        ctx.load_verify_locations(self.certificateChainFile)
        ctx.set_verify(VERIFY_PEER|VERIFY_FAIL_IF_NO_PEER_CERT,
                self._verify)
        ctx.set_verify_depth(10)
        return ctx

    def cacheContext(self):
        DefaultOpenSSLContextFactory.cacheContext(self)

        # Call a callback if defined to check certificate authentificity.
        if self.verifyCallback[0]:
            self._context.set_verify(VERIFY_PEER, self.verifyCertificate)

        if self.certificateChainFile != None:
            self._context.use_certificate_chain_file(self.certificateChainFile)

