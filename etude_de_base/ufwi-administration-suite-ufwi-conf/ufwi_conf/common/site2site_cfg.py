"""
$Id$


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


from IPy import IP
from re import compile

from ufwi_rpcd.common import tr
from ufwi_conf.common.net_exceptions import NuconfException
from ufwi_rpcd.common.abstract_cfg import AbstractConf

from .id_store import IDStore
from .id_store import PersistentID

RSA = 0
PSK = 1

DISCONNECTED = "DISCONNECTED"
PHASE1_OK = "PHASE1_OK"
CONNECTED = "CONNECTED"

class Site2SiteException(NuconfException):
    pass

def none2float(arg, default=0.0):
    return default if arg is None else float(arg)

def _nextFingerprintIdentifier():
    name = "%s %2d" % (tr("Fingerprint"), Fingerprint._ID)
    Fingerprint._ID += 1
    return name

def _nextVPNIdentifier():
    name = "%s %2d" % (tr("IPsec VPN"), VPN._ID)
    VPN._ID += 1
    return name

def _char_to_hex(char):
    return "%x" % ord(char)

def _text_to_hex(text):
    if text == "":
        return text
    return "0x" + "".join(_char_to_hex(char) for char in text)

UNKNOWN_FINGERPRINT = "__ UNKNOWN_FINGERPRINT __"
ESP_REGEX = compile(r'^[-0-9A-Za-z!,_;]*$')
HEX_REGEX = compile(r'^0x[0-9a-fA-F]+$')

class Site2SiteCfg(AbstractConf):
    """
    Changelog:
    1 -> 2
    loudly reworked, bumped DATASTRUCTURE_VERSION to 2.
    Was never in production, no upgrade path provided

    Ensure Fingerprints are restored before VPNs because VPNs need Fingerprints:
    vpns must be after fingerprints in ATTRS
    """
    ATTRS = """
        enabled
        fingerprints
        myfingerprint
        vpns
       """.split()

    DATASTRUCTURE_VERSION = 2

    def __init__(
        self,
        enabled=False,
        vpns=None,
        fingerprints=None,
        myfingerprint="UNKNOWN_FINGERPRINT"):

        if vpns is None:
            #it's useful to have an _ordered_ list in the interface
            vpns = list()
        if fingerprints is None:
            #it's useful to have an _ordered_ list in the interface
            fingerprints = list()
        AbstractConf.__init__(self)

        #don't use self._setLocals(locals())
        self.myfingerprint = myfingerprint
        self.enabled = enabled
        self.fingerprints = fingerprints
        self.vpns = vpns

    @staticmethod
    def defaultConf(myfingerprint=None):
        return Site2SiteCfg(myfingerprint=myfingerprint)

    def isValidWithMsg(self):
        for fingerprint in self.fingerprints:
            ok, msg = fingerprint.isValidWithMsg()
            if not ok:
                return ok, msg

        vpn_identifiers = set()
        for vpn in self.vpns:
            ok, msg = vpn.isValidWithMsg()
            if vpn.identifier in vpn_identifiers:
                return False, tr("VPN identifier must be unique: ") + '%s' % vpn.identifier
            vpn_identifiers.add(vpn.identifier)
            if not ok:
                return ok, msg
        return True, tr("valid configuration")

    def isVpnUsed(self):
        """return True if the service is enabled and there is at least one
        enabled connection"""
        return self.enabled and any(vpn.enabled for vpn in self.vpns)

def _fetch_IP(kwargs, attr):
    val = kwargs.get(attr)
    if not isinstance(val, IP):
        val = IP(val)
    return val

class Fingerprint(AbstractConf, PersistentID):

    DATASTRUCTURE_VERSION = 1
    #see id_store
    ID_OFFSET = 0x3fffffff

    _ID = 0

    STRING_ATTRS = """
        identifier
        fingerprint
        peer
        """.split()

    ATTRS = STRING_ATTRS + ['unique_id',]

    def __init__(self, identifier=None, fingerprint="", peer="", unique_id=None):
        AbstractConf.__init__(self)
        PersistentID.__init__(self, unique_id=unique_id)
        self._fingerprint = None
        if identifier is None:
            identifier = _nextFingerprintIdentifier()

        #don't use self._setLocals(locals()) (or unique_id is set to None)
        self.identifier = identifier
        self.fingerprint = fingerprint
        self.peer = peer

    def _setfingerprint(self, fingerprint):
        self._fingerprint = fingerprint

    def _readfingerprint(self):
        return self._fingerprint

    fingerprint = property(fset=_setfingerprint, fget=_readfingerprint)

    def __str__(self):
        if self.peer == "":
            peer = ''
        else:
            peer = ' associated to %s' % self.peer

        if self.fingerprint == "":
            fingerprint = ''
        else:
            fingerprint = ' [%s]' % self.fingerprint

        return "[%s%s] %s" % (self.identifier, peer, fingerprint)

    def __repr__(self):
        return "<Fingerprint %s>" % str(self)

    # TODO use @recursors (but test recursors before)
    def isValidWithMsg(self):
        for attr in self.STRING_ATTRS:
            value = getattr(self, attr)
            if not isinstance(value, basestring) or (
                attr != "peer" and 0 == len(value)):
                return False, "Invalid %s" % attr

        ok, msg = PersistentID.isValidWithMsg(self)
        if not ok:
            return False, msg

        return True, "Valid configuration"

class VPN(AbstractConf):
    """
    In this class, all attributes but 'key' have types so they are smoothly read and written.

     * rsa is an int
      if it is an int > 0:
        we restore the fingerprint from IDStore.getInstance()
      else: #  0 or -1...
        we are psk based
    """

    _ID = 0

    BOOL_ATTRS = """
        enabled
        pfs""".split()

    STRING_ATTRS = """
        identifier
        esp
        local_network
        public_address
        gateway
        remote_network
        psk
        """.split()

    TIME_ATTRS = """
        key_life
        ike_lifetime
        """.split()

    ATTRS = ["rsa",] + BOOL_ATTRS + STRING_ATTRS + TIME_ATTRS

    DATASTRUCTURE_VERSION = 2

    def __init__(self,
        enabled=True,
        identifier=None,
        local_network="",
        public_address="",
        gateway="",
        remote_network="",
        pfs=False,
        key_life=3600, #seconds
        ike_lifetime=3600, #seconds
        esp="",
        psk="",
        rsa=0):
        AbstractConf.__init__(self)

        if identifier is None:
            identifier = _nextVPNIdentifier()

        self._setLocals(locals())

        self.status = False

    def __set_fingerprint(self, fingerprint):
        self.rsa = fingerprint.unique_id
        self.psk = ""

    def __get_fingerprint(self):
        if self.keytype() == RSA:
            return IDStore.getInstance().uniqueId(self.rsa)
        else:
            self.fingerprint = None

    fingerprint = property(fset=__set_fingerprint, fget=__get_fingerprint)

    def isValid(self):
        ok, msg = self.isValidWithMsg()
        del msg
        return ok

    def isValidWithMsg(self):
        if not self.identifier:
            return False, tr("The VPN identifier should not be empty.")
        if len(self.identifier.split()) > 1:
            return False, tr("The VPN identifier should not contain spaces.")

        if not 0 < self.ike_lifetime <= 28800:
            return False, tr('IKE lifetime expected between Os and 28800s (8h).')

            return False
        if not 0 < self.key_life <= 86400:
            return False, tr('Key lifetime expected between Os and 86400s (24h).')

        try:
            localnet_ip = IP(self.local_network)
        except:
            return False, tr("Local network is not an IP")
        localnet_version = localnet_ip.version()

        try:
            public_ip = IP(self.public_address)
        except:
            return False, tr("Public IP is not an IP")
        if public_ip.version() != localnet_version:
            return False, tr(
                "The IP versions of the local network definition "
                "and the public address IP differ."
                )
        try:
            gateway_ip = IP(self.gateway)
        except:
            return False, tr("Gateway IP is not an IP")
        if gateway_ip.version() != localnet_version:
            return False, tr(
                "The IP versions of the local network definition "
                "and the gateway IP differ."
                )

        try:
            IP(self.remote_network)
        except:
            return False, tr("Remote network IP is not an IP")
        if gateway_ip.version() != localnet_version:
            return False, tr(
                "The IP versions of the local network definition "
                "and the remote network definition differ."
                )

        if self.keytype() == PSK:
            if not isinstance(self.psk, (str, unicode)):
                return False, tr("Invalid key")
        else:
            if not isinstance(self.fingerprint, Fingerprint):
                return False, tr("Invalid key")

        if not ESP_REGEX.match(self.esp):
            return False, tr("Invalid ESP")

        return True, tr("config ok")

    def keytype(self):
        if self.rsa < 1:
            return PSK
        return RSA

