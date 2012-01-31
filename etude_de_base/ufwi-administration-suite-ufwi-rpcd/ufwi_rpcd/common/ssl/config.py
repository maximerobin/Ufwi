
"""
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

from __future__ import with_statement

from sys import getfilesystemencoding
from time import time
from M2Crypto import SSL, X509, m2, ASN1
#from M2Crypto import EVP
from M2Crypto.m2 import SSL_OP_NO_SSLv2, X509_PURPOSE_ANY
from ufwi_rpcd.common.ssl_errors import X509_verify_cert_error_string

from ufwi_rpcd.common import tr
from ufwi_rpcd.common.error import UnicodeException, exceptionAsUnicode
from .info import SSLInfo

class SSLConfigError(UnicodeException):
    pass

class SSLVerifyError:
    def __init__(self, store):
        self.number = store.get_error()
        self.certificate = store.get_current_cert()

    def getMessage(self):
        return X509_verify_cert_error_string(self.number)

    def getCertText(self):
        return unicode(self.certificate.as_text())

    def getSubject(self):
        return unicode(self.certificate.get_subject().as_text())

    def getFingerprint(self):
        return unicode(self.certificate.get_fingerprint())

class SSLConfig:
    EXPECTED_X509_PURPOSE = X509_PURPOSE_ANY

    # Follow debian package vesion numbering convention
    M2CRYPTO_VERSIONS = (M2CRYPTO_0_18_2, M2CRYPTO_TRUNK, M2CRYPTO_0_20_0_EW2) = range(3)

    # Check available m2crypto version
    if hasattr(X509.X509_Store, 'add_crl'):
        m2crypto_version = M2CRYPTO_0_20_0_EW2
    else:
        tmp = ASN1.ASN1_UTCTIME()
        if hasattr(tmp, 'get_datetime'):
            m2crypto_version = M2CRYPTO_TRUNK
        else:
            m2crypto_version = M2CRYPTO_0_18_2

    def __init__(self):
        # Options
        self.fqdn_check = False # Check peers Fqdn
        self.check = False # Check peers certificates
        self.send_cert = True # Always True on server
        self.max_depth = 16
        # 'sslv2', 'sslv23', 'sslv3' or 'tlsv1'
        self.protocol = 'sslv23'   # understand SSLv2, SSLv3 and TLSv1

        # Cipher list:
        #  - start with ALL (all ciphers suites except the eNULL ciphers)
        #  - block ADH: anonymous DH cipher suites
        #  - block LOW: "low" encryption cipher suites, 64 or 56 bit encryption algorithms
        #  - block EXP: export encryption algorithms, including 40 and 56 bits algorithms
        #  - block MD5: cipher suites using MD5
        #  - @STRENGTH: sort the cipher list in order of encryption algorithm key length.
        #
        # See ciphers man page for more information.
        self.cipher_list = 'ALL:!ADH:!LOW:!EXP:!MD5:@STRENGTH'

        # Filenames
        self.ca = u''
        self.cert = u''
        self.key = u''
        self.crl = u''

        # Filesystem charset
        self.fs_charset = getfilesystemencoding()
        if not self.fs_charset:
            self.fs_charset = "utf8"

        # Dynamic patching of M2Crypto to use our certificate checks
        from M2Crypto.SSL.Connection import Connection
        from ufwi_rpcd.common.ssl import Checker
        Connection.clientPostConnectionCheck = Checker(self)

    def setConfig(self, ca = u'', cert = u'', key = u'', crl = u''):
        self.ca = ca
        self.cert = cert
        self.key = key
        self.crl = crl

    def validate(self):
        if self.protocol not in ('sslv2', 'sslv23', 'sslv3', 'tlsv1'):
            return tr("Invalid SSL/TLS protocol: %s") % repr(self.protocol)

        if self.check:
            if not self.ca:
                return tr('You have to provide a CA.')

            # Check the CA
            try:
                ca = X509.load_cert(self.ca)
                if ca.check_ca() == 0:
                    return tr('Specified CA is not a CA certificate')
                ret = self.validate_date(tr('certificate authority'), ca)
                if ret is not None:
                    return ret
            except X509.X509Error, e:
                return tr('Specified CA is not valid: %s') % e

            # TODO: Check CRL

        if self.send_cert:
            if not self.key:
                return tr('You have to provide a private key.')
            if not self.cert:
                return tr('You have to provide a certificate.')
            # Check the certificate
            try:
                cert = X509.load_cert(self.cert)
                if cert.check_purpose(self.EXPECTED_X509_PURPOSE, 0) == 0:
                    return tr('Certificate has an invalid purpose')
                ret = self.validate_date(tr('certificate'), cert)
                if ret is not None:
                    return ret
            except (X509.X509Error, IOError), err:
                return tr('Specified certificate is not valid: %s') % exceptionAsUnicode(err)

            ### Check the private key
            ##try:
            ##    key = EVP.load_key(str(self.key), self.silent_get_password)
            ##    if cert.verify(key) == 0:
            ##        return tr('Certificate and private key don\'t match')
            ##except X509.X509Error, e:
            ##    return tr('Specified private key is not valid: %s') % e

            # Above check will fail if the key is encrypted, perform a simple safety check instead:
            try:
                with open(self.key, "r") as key:
                    key_content = key.read()
                    if "-----BEGIN RSA PRIVATE KEY-----" not in key_content:
                        return tr('The private is not in PEM format')
            except IOError, err:
                return tr('Specified private key is not valid: %s') % exceptionAsUnicode(err)
        return None

    def validate_date(self, user_str, cert):
        # Create UTC timestamp
        try:
            now = ASN1.ASN1_UTCTIME()
            now.set_time(long(time()))
            if now.get_datetime() < cert.get_not_before().get_datetime():
                return tr('Specified %s is not yet valid') % user_str
            if now.get_datetime() > cert.get_not_after().get_datetime():
                return tr('Specified %s is expired') % user_str
        except AttributeError:
            # Ignore error, it's just a test for usability
            # Date validation will still be preformed during the SSL handshake
            pass
        return None

    def encodeFilename(self, filename):
        if isinstance(filename, unicode):
            return filename.encode(self.fs_charset)
        else:
            return filename

    def createContext(self, logger):
        logger.debug("SSL context: protocol=%s, fqdn_check=%s" % (self.protocol, self.fqdn_check))
        context = SSL.Context(self.protocol)
        # Reset options: only disable SSLv2. M2Crypto uses SSL_OP_ALL (enable
        # all bug workarounds), but we control the client and the server and
        # both use the OpenSSL library (a recent version).
        context.set_options(SSL_OP_NO_SSLv2)
        logger.debug("Use cipher list: %s" % self.cipher_list)
        context.set_cipher_list(self.cipher_list)

        if self.send_cert:
            logger.debug("Load certificate chain (%s) and key (%s) files" % (self.cert, self.key))
            try:
                context.load_cert_chain(
                    self.encodeFilename(self.cert),
                    self.encodeFilename(self.key),
                    self.get_key_password)
            except Exception, err:
                raise SSLConfigError(
                    tr("Unable to open the certificate chain or key: %s")
                    % exceptionAsUnicode(err))

        if self.check:
            if self.ca:
                logger.debug("Load certificate authority (%s) file" % self.ca)
                ok = context.load_verify_locations(self.encodeFilename(self.ca))
                if not ok:
                    raise SSLConfigError(
                        tr("Unable to open the certificate authority: %s")
                        % self.ca)
            else:
                logger.info("Warning: No certificate authority")

            if self.crl:
                logger.debug("Load certificate revokation list (%s) file" % self.crl)
                try:
                    crl = X509.load_crl(self.crl)
                except Exception, err:
                    raise SSLConfigError(
                        tr("Unable to open the certificate revokation list: %s")
                        % exceptionAsUnicode(err))
                cert_store = context.get_cert_store()
                try:
                    cert_store.add_crl(crl)
                    cert_store.set_flags(m2.X509_V_FLAG_CRL_CHECK)
                except AttributeError:
                    logger.error("Your m2crypto version doesn't support CRL")
            else:
                logger.info("Warning: No certificate revokation list")

            logger.info("Check SSL peer certificate using M2Crypto")
            mode = SSL.verify_peer
            mode |= SSL.verify_fail_if_no_peer_cert
            context.set_verify(mode, self.max_depth, self.m2_verif_cert)
        else:
            logger.info("Warning: unsafe encrypted connection (SSL), don't check the peer certificate")
            context.set_verify(SSL.verify_none, 0, None)

        context.set_info_callback(self._ssl_info)

        # move fqdn checking code here (it's currently done in ufwi_rpcd/common/ssl/checker.py)
        return context

    def m2_verif_cert(self, ok, store):
        if not ok:
            error = SSLVerifyError(store)
            return self.user_verify(error)
        else:
            return ok

    def _ssl_info(self, where, ret, ssl_ptr):
        info = SSLInfo(where, ret, ssl_ptr)
        self.sslInfo(info)

    def user_verify(self, error):
        # Basic implementation printing the error to stdout.
        # You should write your own implementation
        print 'Certificate verification of "%s" failed: %s' \
            % (error.getSubject(), error.getMessage())
        # deny invalid certificate
        return 0

    def get_key_password(self, v):
        # Dummy implementation
        # You should write your own implementation
        print 'Encrypted keys not implemented'
        return ''

    def silent_get_password(self, v):
        # Silently return no password during certificate / private key checks
        return ''

    @classmethod
    def getM2CryptoVersionWarning(cls):
        # No warning on latest version
        if cls.m2crypto_version == len(cls.M2CRYPTO_VERSIONS) - 1:
            return None

        implements = {
            cls.M2CRYPTO_0_18_2 : None,
            cls.M2CRYPTO_TRUNK : tr('- Dates validity checks during certificates setup'),
            cls.M2CRYPTO_0_20_0_EW2 : tr('- Certificates validation against a CRL'),
        }

        warning = tr("Warning, your M2Crypto version doesn't handle :\n")
        lines = [warning]
        for missing in xrange(cls.m2crypto_version + 1, len(cls.M2CRYPTO_VERSIONS)):
            lines.append(implements[missing])
        return lines

    # Override this method to process SSL informations.
    def sslInfo(self, info):
        # info: SSLInfo object
        pass

