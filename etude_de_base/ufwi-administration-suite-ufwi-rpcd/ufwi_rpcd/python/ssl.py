# Copy of Lib/ssl.py from Python trunk (rev 68092)
# Patches:
#  - replace "except SSLError as x:" by "except SSLError, x:"
#  - replace "from _ssl import SSLError" by "from _ssl import sslerror as SSLError"
#  - replace "_ssl.sslwrap" by "_ssl.ssl"
#  - remove "from _ssl import CERT_NONE, CERT_OPTIONAL, CERT_REQUIRED"
#  - remove "from _ssl import PROTOCOL_SSLv2, PROTOCOL_SSLv3, PROTOCOL_SSLv23, PROTOCOL_TLSv1"
#  - remove "get_protocol_name"
#  - remove "ssl_version=PROTOCOL_SSLv23," option
#  - remove "server_side=False" option
#  - remove "cert_reqs" and "ca_certs" options
#  - remove "do_handshake_on_connect" option
#  - remove "suppress_ragged_eofs" option

# Wrapper module for _ssl, providing some additional facilities
# implemented in Python.  Written by Bill Janssen.

"""\
This module provides some more Pythonic support for SSL.

Object types:

  SSLSocket -- subtype of socket.socket which does SSL over the socket

Exceptions:

  SSLError -- exception raised for I/O errors

Functions:

  cert_time_to_seconds -- convert time string used for certificate
                          notBefore and notAfter functions to integer
                          seconds past the Epoch (the time values
                          returned from time.time())

  fetch_server_certificate (HOST, PORT) -- fetch the certificate provided
                          by the server running on HOST at port PORT.  No
                          validation of the certificate is performed.

Integer constants:

SSL_ERROR_ZERO_RETURN
SSL_ERROR_WANT_READ
SSL_ERROR_WANT_WRITE
SSL_ERROR_WANT_X509_LOOKUP
SSL_ERROR_SYSCALL
SSL_ERROR_SSL
SSL_ERROR_WANT_CONNECT

SSL_ERROR_EOF
SSL_ERROR_INVALID_ERROR_CODE

The following constants identify various SSL protocol variants:

PROTOCOL_SSLv2
PROTOCOL_SSLv3
PROTOCOL_SSLv23
PROTOCOL_TLSv1


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


import textwrap

import _ssl             # if we can't import it, let the error propagate

from _ssl import sslerror as SSLError
from _ssl import RAND_status, RAND_egd, RAND_add
from _ssl import \
     SSL_ERROR_ZERO_RETURN, \
     SSL_ERROR_WANT_READ, \
     SSL_ERROR_WANT_WRITE, \
     SSL_ERROR_WANT_X509_LOOKUP, \
     SSL_ERROR_SYSCALL, \
     SSL_ERROR_SSL, \
     SSL_ERROR_WANT_CONNECT, \
     SSL_ERROR_EOF, \
     SSL_ERROR_INVALID_ERROR_CODE

from socket import socket, _fileobject, error as socket_error
from socket import getnameinfo as _getnameinfo
import base64        # for DER-to-PEM translation

class SSLSocket (socket):

    """This class implements a subtype of socket.socket that wraps
    the underlying OS socket in an SSL context when necessary, and
    provides read and write methods over that channel."""

    def __init__(self, sock, keyfile=None, certfile=None):
        socket.__init__(self, _sock=sock._sock)
        # the initializer for socket trashes the methods (tsk, tsk), so...
        self.send = lambda data, flags=0: SSLSocket.send(self, data, flags)
        self.sendto = lambda data, addr, flags=0: SSLSocket.sendto(self, data, addr, flags)
        self.recv = lambda buflen=1024, flags=0: SSLSocket.recv(self, buflen, flags)
        self.recvfrom = lambda addr, buflen=1024, flags=0: SSLSocket.recvfrom(self, addr, buflen, flags)
        self.recv_into = lambda buffer, nbytes=None, flags=0: SSLSocket.recv_into(self, buffer, nbytes, flags)
        self.recvfrom_into = lambda buffer, nbytes=None, flags=0: SSLSocket.recvfrom_into(self, buffer, nbytes, flags)

        if certfile and not keyfile:
            keyfile = certfile
        # see if it's connected
        try:
            socket.getpeername(self)
        except socket_error:
            # no, no connection yet
            self._sslobj = None
        else:
            # yes, create the SSL object
            self._sslobj = _ssl.ssl(self._sock, keyfile, certfile)
            timeout = self.gettimeout()
            try:
                self.settimeout(None)
                self.do_handshake()
            finally:
                self.settimeout(timeout)
        self.keyfile = keyfile
        self.certfile = certfile
        self._makefile_refs = 0

    def read(self, len=1024):

        """Read up to LEN bytes and return them.
        Return zero-length string on EOF."""

        try:
            return self._sslobj.read(len)
        except SSLError, x:
            if x.args[0] == SSL_ERROR_EOF:
                return ''
            else:
                raise

    def write(self, data):

        """Write DATA to the underlying SSL channel.  Returns
        number of bytes of DATA actually transmitted."""

        return self._sslobj.write(data)

    def getpeercert(self, binary_form=False):

        """Returns a formatted version of the data in the
        certificate provided by the other end of the SSL channel.
        Return None if no certificate was provided, {} if a
        certificate was provided, but not validated."""

        return self._sslobj.peer_certificate(binary_form)

    def cipher (self):

        if not self._sslobj:
            return None
        else:
            return self._sslobj.cipher()

    def send (self, data, flags=0):
        if self._sslobj:
            if flags != 0:
                raise ValueError(
                    "non-zero flags not allowed in calls to send() on %s" %
                    self.__class__)
            while True:
                try:
                    v = self._sslobj.write(data)
                except SSLError, x:
                    if x.args[0] == SSL_ERROR_WANT_READ:
                        return 0
                    elif x.args[0] == SSL_ERROR_WANT_WRITE:
                        return 0
                    else:
                        raise
                else:
                    return v
        else:
            return socket.send(self, data, flags)

    def sendto (self, data, addr, flags=0):
        if self._sslobj:
            raise ValueError("sendto not allowed on instances of %s" %
                             self.__class__)
        else:
            return socket.sendto(self, data, addr, flags)

    def sendall (self, data, flags=0):
        if self._sslobj:
            if flags != 0:
                raise ValueError(
                    "non-zero flags not allowed in calls to sendall() on %s" %
                    self.__class__)
            amount = len(data)
            count = 0
            while (count < amount):
                v = self.send(data[count:])
                count += v
            return amount
        else:
            return socket.sendall(self, data, flags)

    def recv (self, buflen=1024, flags=0):
        if self._sslobj:
            if flags != 0:
                raise ValueError(
                    "non-zero flags not allowed in calls to sendall() on %s" %
                    self.__class__)
            while True:
                try:
                    return self.read(buflen)
                except SSLError, x:
                    if x.args[0] == SSL_ERROR_WANT_READ:
                        continue
                    else:
                        raise x
        else:
            return socket.recv(self, buflen, flags)

    def recv_into (self, buffer, nbytes=None, flags=0):
        if buffer and (nbytes is None):
            nbytes = len(buffer)
        elif nbytes is None:
            nbytes = 1024
        if self._sslobj:
            if flags != 0:
                raise ValueError(
                  "non-zero flags not allowed in calls to recv_into() on %s" %
                  self.__class__)
            while True:
                try:
                    tmp_buffer = self.read(nbytes)
                    v = len(tmp_buffer)
                    buffer[:v] = tmp_buffer
                    return v
                except SSLError, x:
                    if x.args[0] == SSL_ERROR_WANT_READ:
                        continue
                    else:
                        raise x
        else:
            return socket.recv_into(self, buffer, nbytes, flags)

    def recvfrom (self, addr, buflen=1024, flags=0):
        if self._sslobj:
            raise ValueError("recvfrom not allowed on instances of %s" %
                             self.__class__)
        else:
            return socket.recvfrom(self, addr, buflen, flags)

    def recvfrom_into (self, buffer, nbytes=None, flags=0):
        if self._sslobj:
            raise ValueError("recvfrom_into not allowed on instances of %s" %
                             self.__class__)
        else:
            return socket.recvfrom_into(self, buffer, nbytes, flags)

    def pending (self):
        if self._sslobj:
            return self._sslobj.pending()
        else:
            return 0

    def unwrap (self):
        if self._sslobj:
            s = self._sslobj.shutdown()
            self._sslobj = None
            return s
        else:
            raise ValueError("No SSL wrapper around " + str(self))

    def shutdown (self, how):
        self._sslobj = None
        socket.shutdown(self, how)

    def close (self):
        if self._makefile_refs < 1:
            self._sslobj = None
            socket.close(self)
        else:
            self._makefile_refs -= 1

    def do_handshake (self):

        """Perform a TLS/SSL handshake."""
        # FIXME: self._sslobj.do_handshake()
        pass

    def connect(self, addr):

        """Connects to remote ADDR, and then wraps the connection in
        an SSL channel."""

        # Here we assume that the socket is client-side, and not
        # connected at the time of the call.  We connect it, then wrap it.
        if self._sslobj:
            raise ValueError("attempt to connect already-connected SSLSocket!")
        socket.connect(self, addr)
        self._sslobj = _ssl.ssl(self._sock, self.keyfile, self.certfile)
        self.do_handshake()

    def accept(self):

        """Accepts a new connection from a remote client, and returns
        a tuple containing that new connection wrapped with a server-side
        SSL channel, and the address of the remote client."""

        newsock, addr = socket.accept(self)
        return (SSLSocket(newsock,
                          keyfile=self.keyfile,
                          certfile=self.certfile),
                addr)

    def makefile(self, mode='r', bufsize=-1):

        """Make and return a file-like object that
        works with the SSL connection.  Just use the code
        from the socket module."""

        self._makefile_refs += 1
        return _fileobject(self, mode, bufsize)



def wrap_socket(sock, keyfile=None, certfile=None):

    return SSLSocket(sock, keyfile=keyfile, certfile=certfile)


# some utility functions

def cert_time_to_seconds(cert_time):

    """Takes a date-time string in standard ASN1_print form
    ("MON DAY 24HOUR:MINUTE:SEC YEAR TIMEZONE") and return
    a Python time value in seconds past the epoch."""

    import time
    return time.mktime(time.strptime(cert_time, "%b %d %H:%M:%S %Y GMT"))

PEM_HEADER = "-----BEGIN CERTIFICATE-----"
PEM_FOOTER = "-----END CERTIFICATE-----"

def DER_cert_to_PEM_cert(der_cert_bytes):

    """Takes a certificate in binary DER format and returns the
    PEM version of it as a string."""

    if hasattr(base64, 'standard_b64encode'):
        # preferred because older API gets line-length wrong
        f = base64.standard_b64encode(der_cert_bytes)
        return (PEM_HEADER + '\n' +
                textwrap.fill(f, 64) +
                PEM_FOOTER + '\n')
    else:
        return (PEM_HEADER + '\n' +
                base64.encodestring(der_cert_bytes) +
                PEM_FOOTER + '\n')

def PEM_cert_to_DER_cert(pem_cert_string):

    """Takes a certificate in ASCII PEM format and returns the
    DER-encoded version of it as a byte sequence"""

    if not pem_cert_string.startswith(PEM_HEADER):
        raise ValueError("Invalid PEM encoding; must start with %s"
                         % PEM_HEADER)
    if not pem_cert_string.strip().endswith(PEM_FOOTER):
        raise ValueError("Invalid PEM encoding; must end with %s"
                         % PEM_FOOTER)
    d = pem_cert_string.strip()[len(PEM_HEADER):-len(PEM_FOOTER)]
    return base64.decodestring(d)

def get_server_certificate (addr):

    """Retrieve the certificate from the server at the specified address,
    and return it as a PEM-encoded string."""

    host, port = addr
    s = wrap_socket(socket())
    s.connect(addr)
    dercert = s.getpeercert(True)
    s.close()
    return DER_cert_to_PEM_cert(dercert)


# a replacement for the old socket.ssl function

def sslwrap_simple (sock, keyfile=None, certfile=None):

    """A replacement for the old socket.ssl function.  Designed
    for compability with Python 2.5 and earlier.  Will disappear in
    Python 3.0."""

    if hasattr(sock, "_sock"):
        sock = sock._sock

    ssl_sock = _ssl.sslwrap(sock, keyfile, certfile)
    try:
        sock.getpeername()
    except socket_error:
        # no, no connection yet
        pass
    else:
        # yes, do the handshake
        ssl_sock.do_handshake()

    return ssl_sock
