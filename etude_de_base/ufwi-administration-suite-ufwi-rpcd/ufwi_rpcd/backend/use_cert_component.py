"""
Copyright (C) 2010-2011 EdenWall Technologies

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

from hashlib import md5
from os import umask
from os.path import exists, isfile
from tempfile import NamedTemporaryFile

from M2Crypto.X509 import load_cert, load_crl

from twisted.internet.defer import inlineCallbacks

from ufwi_rpcd.backend import tr
from ufwi_rpcd.backend.component import Component
from ufwi_rpcd.backend.error import RpcdError
from ufwi_rpcd.common.download import getEncodedFileContent
from ufwi_rpcd.common.logger import LoggerChild
from ufwi_rpcd.common.ssl.config import SSLConfig
from ufwi_rpcd.common.download import decodeFileContent
from ufwi_rpcd.core.context import Context

class UseCertificateComponent(object):
    CERT_PATH = None
    KEY_PATH =  None
    CA_PATH =   None
    CRL_PATH =  None

    CERT_OWNER_AND_GROUP = "root", "root"

    def __init__(self):
        if not isinstance(self, Component):
            raise NotImplementedError("This class has to be inherited by a Component class")
        self.core = None
        self.CERT_ATTR_TO_PATH = None
        self.cert_logger = LoggerChild(self)
        self.CERT_ATTR_TO_PATH = {
            'key' :     self.KEY_PATH,
            'cert' :    self.CERT_PATH,
            'ca' :      self.CA_PATH,
            'crl' :     self.CRL_PATH,
        }

    def init(self, core):
        self.core = core
        self.core.notify.connect('nupki', 'updateCRL', self._nupkiCRLUpdated)

    def service_getCertificatesInfo(self, ctx):
        """
        Return information about certifiates/eky currently set, in the form of a dictionnary:
        {
            'cert'  : ['brief description', 'certificate content'],
            'key'   : ['md5 of the key', ''],
            'ca'    : ['brief description', 'CA content'],
            'crl'   : ['brief description', 'CRL content'],
        }
        """
        infos = {
            'cert' :    [tr('No certificate set'), tr('No certificate has been set yet')],
            'key' :     [tr('No key set'), ''],
            'ca' :      [tr('No CA is set'), tr('No certificate authority has been set yet')],
            'crl' :     [tr('No CRL set'), tr('No certificate revocation list has been set yet')],
        }

        # Certificate
        try:
            if isfile(self.CERT_PATH):
                cert = load_cert(self.CERT_PATH)
                infos['cert'][0] = unicode(cert.get_subject())
                infos['cert'][1] = unicode(cert.as_text())
        except Exception, error:
            infos['cert'][0] = tr('Invalid certificate')
            self.cert_logger.debug("Invalid cert : %s" % error)

        # Private key
        try:
            if isfile(self.KEY_PATH):
                with open(self.KEY_PATH, 'rb') as key:
                    hash_md5 = md5()
                    hash_md5.update(key.read())
                    infos['key'][0] = u'MD5: ' + unicode(hash_md5.hexdigest())
        except Exception, error:
            infos['key'][0] = tr('Invalid key')
            self.cert_logger.debug("Invalid key : %s" % error)

        # CA
        try:
            if isfile(self.CA_PATH):
                cert = load_cert(self.CA_PATH)
                infos['ca'][0] = unicode(cert.get_subject())
                infos['ca'][1] = unicode(cert.as_text())
        except Exception, error:
            infos['ca'][0] = tr('Invalid CA')
            self.cert_logger.debug("Invalid CA : %s" % error)

        # CRL
        try:
            if isfile(self.CRL_PATH):
                crl = load_crl(self.CRL_PATH)
                infos['crl'][0] = tr('CRL set')
                infos['crl'][1] = unicode(crl.as_text())
        except Exception, error:
            infos['crl'][0] = tr('Invalid CRL')
            self.cert_logger.debug("Invalid CRL : %s" % error)

        return infos

    @inlineCallbacks
    def _setSSLConfig(self, config):
        nupki = config.get('use_nupki', False)
        if nupki:
            yield self._setSSLConfigNuPKI(config)
        else:
            yield self._setSSLConfigFiles(config)
        self.cert_logger.critical("New certificates installed.")

    @inlineCallbacks
    def _setSSLConfigNuPKI(self, config):
        pki = config.get('nupki_pki', u'')
        cert = config.get('nupki_cert', u'')

        self.cert_logger.error('Copy certificate "%s" of the PKI "%s".' % (cert, pki))

        comp_ctx = Context.fromComponent(self)
        yield self.core.callService(comp_ctx, 'nupki', 'copyPKI', pki, cert,
            {'ca': self.CA_PATH,
             'certificate': self.CERT_PATH,
             'key': self.KEY_PATH,
             'crl': self.CRL_PATH})

    def _setSSLConfigFiles(self, config):
        if not config['disable_crl'] and not config['crl']:
            ## Check a crl has previously been uploaded:
            try:
                with open(self.CRL_PATH, 'r') as fp:
                    fp.read()
            except IOError:
                raise RpcdError(tr("No CRL has previously been uploaded. CRL check cannot be enabled."))

        tmp_file = {}
        tmp_ssl_config = SSLConfig()
        tmp_ssl_options = {}

        self.warning('Validate uploaded certificate')

        umask(0177)
        for key in self.CERT_ATTR_TO_PATH.keys():
            if not config[key]:
                continue
            content = decodeFileContent(config[key])

            tmp_file[key] = NamedTemporaryFile("wb")
            tmp_file[key].write(content)
            tmp_file[key].flush()
            tmp_ssl_options[key] = tmp_file[key].name

        tmp_ssl_config.setConfig(**tmp_ssl_options)

        # Check key and cert if one of the 2 was provided
        tmp_ssl_config.send_cert = False
        if 'cert' in config and config['cert']:
            tmp_ssl_config.send_cert = True
        if 'key' in config and config['key']:
            tmp_ssl_config.send_cert = True

        # Check ca and crl if one of the 2 was provided
        if 'ca' in config and config['ca']:
            tmp_ssl_config.check = True
        if 'crl' in config and config['crl']:
            tmp_ssl_config.check = True

        validation = tmp_ssl_config.validate()

        for key in self.CERT_ATTR_TO_PATH.keys():
            if key in tmp_file:
                tmp_file[key].close()

        if validation is not None:
            raise RpcdError(validation)

        self.warning('Write the uploaded certificate')
        # FIXME: use a transaction to write PEM files
        for key in self.CERT_ATTR_TO_PATH.keys():
            if not config[key]:
                continue
            with open(self.CERT_ATTR_TO_PATH[key], 'w') as fp:
                fp.write(decodeFileContent(config[key]))

    @inlineCallbacks
    def _nupkiCRLUpdated(self, notify_context):
        config = self._getSSLConfig()
        if not config['use_nupki']:
            return
        pki_name = notify_context.pki_name
        if config['nupki_pki'] != pki_name:
            return
        self.cert_logger.error("Copy updated PKI CRL")

        context = Context.fromComponent(self)
        yield self.core.callService(context, 'nupki', 'copyCRL', pki_name, self.CRL_PATH)
        self._onCRLUpdated()

    def _getSSLConfig(self):
        raise NotImplementedError()

    def _onCRLUpdated(self):
        pass

    def upgradeFields(self, serialized):
        """
        upgrade from 2 to 3 if nupki not used (if nupki is used, code in
        common know how upgrade)
        if unsuccessful reraise error
        """
        if not(2 == serialized['DATASTRUCTURE_VERSION'] and not serialized['use_pki']):
            return

        serialized['use_nupki'] = False
        serialized['nupki_pki'] = u''
        serialized['nupki_cert'] = u''

        attr2path = {
            'ca': self.CA_PATH,
            'cert': self.CERT_PATH,
            'key': self.KEY_PATH,
        }
        for key, crt_path in attr2path.items():
            if exists(crt_path):
                serialized[key] = getEncodedFileContent(crt_path)
            else:
                serialized[key] = u''

        serialized['disable_crl'] = exists(self.CRL_PATH)
        if serialized['disable_crl']:
            serialized['crl'] = getEncodedFileContent(self.CRL_PATH)
        else:
            serialized['crl'] = u''

        del serialized['certificate']
        del serialized['use_pki']
        serialized['DATASTRUCTURE_VERSION'] = 3

    def setCertsOwnership(self):
        for cert_file in self.CERT_ATTR_TO_PATH.values():
            self.chownWithNames(cert_file, *self.CERT_OWNER_AND_GROUP)

