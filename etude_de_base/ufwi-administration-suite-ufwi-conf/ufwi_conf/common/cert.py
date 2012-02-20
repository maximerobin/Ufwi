#coding: utf-8
"""
Copyright (C) 2010-2011 EdenWall Technologies
"""

from ufwi_rpcd.common.tools import toUnicode

class CertConf(object):

    # Version 3:
    #  - rename certificate to nupki_cert
    #  - rename use_pki to nupki_pki
    #  - create fields use_nupki, cert, key, ca and crl


    ATTRS="""
        ca
        cert
        crl
        key
        nupki_pki
        nupki_cert
        use_nupki
        disable_crl
        """.split()

    def __init__(self, ca='', cert='', crl='', key='', nupki_pki='', nupki_cert=u'', use_nupki='',
            disable_crl=False):
        self.ca = ca
        self.cert = cert
        self.crl = crl
        self.key = key
        self.use_nupki = use_nupki
        self.nupki_cert = nupki_cert
        self.nupki_pki = nupki_pki
        self.disable_crl = disable_crl

    def setUsePKI(self, value):
        if value:
            self.use_pki = toUnicode(value)
        else:
            self.use_pki = u''

    def setCertificate(self, filename):
        self.certificate = unicode(filename)

    def setKey(self, filename):
        self.key = unicode(filename)

    def setCA(self, filename):
        self.ca = unicode(filename)

    def setCRL(self, filename):
        self.crl = unicode(filename)

    def getSSLDict(self):
        d = {}
        for attr in CertConf.ATTRS:
            d[attr] = getattr(self, attr)
        return d

    def setSSLDict(self, d):
        for attr in CertConf.ATTRS:
            setattr(self, attr, d[attr])

    # checkSerialVersion/downgradeFields called by subclasses class to handle versions compatibilty
    # use checkSerialVersion[A-Z] to specify version number (as the version no is defined in the subclass)
    @classmethod
    def checkSerialVersionA(cls, datastructure_version, serialized):

        if datastructure_version < 3:
            # Upgrade 2 -> 3:
            #CertConf upgraded

            # fix pki fields:
            serialized['use_nupki'] = bool(serialized['use_pki'])
            serialized['nupki_pki'] = serialized['use_pki']
            serialized['nupki_cert'] = serialized['certificate']
            serialized['ca'] = u''
            serialized['key'] = u''
            serialized['crl'] = u''
            serialized['cert'] = u''
            del serialized['certificate']
            del serialized['use_pki']

            # enable the CRL if one was set
            serialized['disable_crl'] = True

    @classmethod
    def downgradeFieldsA(cls, serialized):
        # fix pki fields:
        # Downgrade 3 -> 2:
        if serialized.get('use_nupki', False):
            serialized['use_pki'] = serialized['nupki_pki']
            serialized['certificate'] = serialized['nupki_cert']
        else:
            serialized['use_pki'] = False
            serialized['certificate'] = u''
        serialized['key'] = u''
        serialized['ca'] = u''
        serialized['crl'] = u''
        for key in 'use_nupki nupki_pki nupki_cert cert disable_crl'.split():
            if key in serialized:
                del serialized[key]

        # remove the CRL field (old comment)

