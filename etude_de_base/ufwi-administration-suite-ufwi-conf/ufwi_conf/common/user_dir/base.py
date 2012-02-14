#coding: utf-8

"""
New nuauth config system

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

from ufwi_rpcd.common.abstract_cfg import AbstractConf
from ufwi_rpcd.common import tr
from ufwi_rpcd.common.radius_client import RadiusConf
from ufwi_rpcd.common.validators import check_ip_or_domain, check_port, check_domain, check_hostname

from ..utils import typedproperty, textlineproperty, WORDproperty
from .ldap import cleanuri, dnproperty, valid_dn
from .protocols import (
    AD, NND, KERBEROS, KERBEROS_AD, LDAP, RADIUS, REQCERT_ALLOW,
    REQCERT_VALUES, SAME, SSL_DISABLED, NOT_CONFIGURED,
    validcombinationsWithMsg
    )
from .tests import has_ldaps
from .upgrade import upgradeNuauthCfg

CUSTOM, NUPKI = 'CUSTOM', 'NUPKI'

NND_DIRTYPES = AD, LDAP, EDIRECTORY = AD, LDAP, "edirectory"

_VALID_CONFIG_MSG = tr("Valid configuration")

class AbstractUserdir(AbstractConf):
    """
    The base type for NuauthCfg members
    """
    protocol = None

class AbstractAuth(AbstractUserdir):
    """
    The base type for NuauthCfg auth member
    """
    pass

class NotConfiguredAuth(AbstractAuth):
    DATASTRUCTURE_VERSION = 3
    protocol = NOT_CONFIGURED

    def isValidWithMsg(self):
        return (True, _VALID_CONFIG_MSG)

class AbstractOrg(AbstractUserdir):
    """
    The base type for NuauthCfg org member
    """
    pass

class NotConfiguredOrg(AbstractOrg):
    DATASTRUCTURE_VERSION = 3
    protocol = NOT_CONFIGURED

    def isValidWithMsg(self):
        return (True, _VALID_CONFIG_MSG)

class NuauthCfg(AbstractConf):
    DATASTRUCTURE_VERSION = 4

    ATTRS = """
    auth
    org
    """.split()
    def __init__(self, auth=None, org=None):
        """
        Default values for auth/org: same empty ldap server for auth and org
        """
        self.__ldap_cert_present = False
        AbstractConf.__init__(self)
        if auth is None:
            auth = NotConfiguredAuth()
        if org is None:
            org = NotConfiguredOrg()
        self._setLocals(locals())

    auth = typedproperty(AbstractAuth, 'auth')
    org = typedproperty(AbstractOrg, 'org')

    def isConfigured(self):
        return not isinstance(self.auth, NotConfiguredAuth)

    def isValid(self, use_state=False):
        ok, msg = self.isValidWithMsg(use_state=use_state)
        del msg
        return ok

    def isValidWithMsg(self, use_state=False):
        """
        return a tuple (is_config_valid, 'message if invalid')
        """

        ok_comb, msg_comb = \
            validcombinationsWithMsg(self.auth.protocol, self.org.protocol)
        if not ok_comb:
            return False, msg_comb

        ok_auth, msg_auth = self.auth.isValidWithMsg()
        ok_org, msg_org = self.org.isValidWithMsg()


        if ok_auth and ok_org:
            return True, _VALID_CONFIG_MSG

        if ok_auth:
            return False, msg_org

        if ok_org:
            return False, msg_auth

        return False, '\n'.join((msg_auth, msg_org))

    def getAuthType(self):
        if self.auth.protocol == SAME:
            return self.org.protocol
        return self.auth.protocol

    @classmethod
    def checkSerialVersion(cls, serialized):
        datastructure_version = serialized.get('DATASTRUCTURE_VERSION')
        supported_versions = (1, 2, 3, 4)
        if datastructure_version not in supported_versions:

            #This will raise relevant errors
            cls.raise_version_error(datastructure_version)
        elif datastructure_version < 2:
            #upgrade
            #1 -> 2: add manual_pushed_routes
            serialized['manual_pushed_routes'] = ()
        return datastructure_version

    #ldap things
    def setLdapCertPresent(self, is_present):
        if self.org.protocol == LDAP:
            self.org.server_cert_set = is_present
        #else, ignore: this is a convenience method

    def getLdapCertPresent(self):
        if self.org.protocol == LDAP:
            return self.org.server_cert_set
        return False

    def getReqcertPolicy(self):
        if self.org.protocol == LDAP:
            return self.org.reqcert
        return REQCERT_ALLOW

    #ad things
    def hasAD(self):
        return self.org.protocol == AD

    @classmethod
    def deserialize(cls, serialized):
        if serialized.get('DATASTRUCTURE_VERSION', 1) < 3:
            serialized = upgradeNuauthCfg(serialized)

            return NuauthCfg.deserialize(serialized)

        return NuauthCfg._deserialize(serialized)

class SameAsOrgAuth(AbstractAuth):
    """
    Simplest auth type:
    takes values from org member
    """
    DATASTRUCTURE_VERSION = 1
    protocol = SAME

    def isValidWithMsg(self):
        return True, tr("Valid authentication configuration")

class RadiusAuth(RadiusConf, AbstractAuth):
    """
    Checks username and password against a radius server

    Inherits RadiusConf, AbstractAuth.
    MRO: RadiusConf's methods prime over AbstractAuth's
    """
    protocol = RADIUS
    def __init__(self, servers=None):
        RadiusConf.__init__(self, servers=servers)


def textproperty(attrname):
    real_attrname = '__%s' % attrname
    default = u''

    def setter(self, value):

        if not value:
            value = default
        setattr(self, real_attrname, value.strip())

    def getter(self):
        return getattr(self, real_attrname, default)

    setattr(setter, '__name__', '_set%s' % attrname)
    setattr(getter, '__name__', '_get%s' % attrname)

    return property(fset=setter, fget=getter)

class LDAPOrg(AbstractOrg):
    DATASTRUCTURE_VERSION = 1
    protocol = LDAP
    TEXT_ATTRS = """
        dn_users
        dn_groups
        user
        password
        """.split()

    ATTRS = TEXT_ATTRS + """
        uri
        custom_or_nupki
        reqcert
        server_cert_set
    """.split()

    def __init__(self,
        uri=None,
        dn_users=None,
        dn_groups=None,
        user="",
        password="",
        custom_or_nupki=SSL_DISABLED,
        reqcert=REQCERT_ALLOW,
        server_cert_set=False
        ):
        AbstractOrg.__init__(self)

        #happy pylint
        self.uri = self.dn = self.user = self.password = \
        self.custom_or_nupki = self.reqcert = self.server_cert_set = None

        self._setLocals(locals())

    user = textproperty('user')
    password = textproperty('password')
    dn_groups = textproperty('dn_groups')
    dn_users = textproperty('dn_users')

    def setUri(self, uri):
        self.uri = cleanuri(uri)

    def isValidWithMsg(self):
        for method in (
            self._valid_noMissingAttr,
            self._valid_uriWithMsg,
            self._valid_DNUsersWithMsg,
            self._valid_DNGroupsWithMsg,
            self._valid_UserWithMsg,
            self._valid_reqcertWithMsg
        ):
            ok, msg = method()
            if not ok:
                return False, msg

        return True, ''

    def _valid_noMissingAttr(self):
        for attr in self.__class__.ATTRS:
            if getattr(self, attr) is None:
                return False, tr("%(VALUE)s is unset.") % {"VALUE": attr}
        return True, ''

    def _valid_uriWithMsg(self):
        if not isinstance(self.uri, (str, unicode)):
            return False, tr(
                    "uri attr is not of expected type (found %(TYPE)s)",
                    "technical message, should not appear to users"
                ) % {"TYPE": type(self.uri)}

        if len(self.uri.strip()) == 0:
            return False, tr("uri is empty.")
        return True, ''

    def _valid_DNUsersWithMsg(self):
        if not self.dn_users:
            return False, tr("LDAP DN for users is empty.")
        if not valid_dn(self.dn_users):
            return False, tr("LDAP DN for users: syntax is invalid.")
        return True, ''

    def _valid_DNGroupsWithMsg(self):
        if not self.dn_groups:
            return False, tr("LDAP DN for groups is empty.")
        if not valid_dn(self.dn_groups):
            return False, tr("LDAP DN for groups: syntax is invalid.")
        return True, ''

    def _valid_UserWithMsg(self):
        if bool(self.user) == bool(self.password):
            if len(self.user) == 0 and len(self.password) == 0:
                return True, ''
            else:
                if not valid_dn(self.user):
                    return False, tr('Login syntax for binding on LDAP server is invalid.')
        elif bool(self.user) != bool(self.password):
            return False, tr("User and password can be both blank, but not only one of them")

        return True, ''

    def _valid_reqcertWithMsg(self):
        if self.reqcert not in REQCERT_VALUES:
            return (
                False,
                tr("reqcert attr is not in expected values "
                "(found '%(FOUND)s', expected one of %(POSSIBILITIES)s)",
                "technical message") %
                {"FOUND":self.reqcert, "POSSIBILITIES": REQCERT_VALUES}
                )
        return True, ''


    def generateTest(self):
        dc = self.user
        if dc is None:
            dc = ''

        base = self.dn_users
        if base is None or base == '':
            base = dc

        password = self.password
        if password is None:
            password = ''

        uri = self.uri
        query_filter = dc.split(',')[0]
        return dc, base, uri, query_filter, password

def _ad_valid_passwordserver_item(word):
    if word == "*":
        return True

    fqdn = ''

    if word.find(':') != -1:
        parsed = word.split(':')
        if len(parsed) != 2:
            return False
        fqdn, port = parsed
        if not check_port(port):
            return False
    else:
        fqdn = word

    return check_ip_or_domain(fqdn)

def _ad_valid_passwordserver(value):
    if not isinstance(value, (str, unicode)):
        #Don't translate, this happens in dev environment only I hope
        return False, \
            tr("'Password server' (controller_ip) attr is not "\
            "of expected type (found %(TYPE)s)",
            "technical message") % {"TYPE": type(value)}

    if len(value.strip()) == 0:
        return False, tr("The 'Password server' field is empty.")

    words = value.split()
    for word in words:
        if not _ad_valid_passwordserver_item(word):
            return False, tr(
            "As a 'Password server' value, this value "\
            "is not understood:") + word

    if len(words) != len(set(words)):
        return False, tr("There should not be duplicates in the authentication server field.")

    return True, ''

class ADOrg(AbstractOrg):
    DATASTRUCTURE_VERSION = 1
    protocol = AD
    ATTRS = """
           controller_ip
           domain
           dns_domain
           workgroup
           user
           password
           wins_ip
           """.split()

    COMPULSORY_ATTRS = """
        controller_ip
        domain
        user
        password
        """.split()

    def __init__(self, controller_ip=None, domain=None, dns_domain=None,
                workgroup=None, user=None, password=None, wins_ip=None):
        AbstractOrg.__init__(self)

        #happy pylint
        self.controller_ip = \
        self.domain = \
        self.dns_domain = \
        self.workgroup = \
        self.user = \
        self.password = \
        self.wins_ip = None

        self._setLocals(locals())

        if not self.dns_domain:
            self.dns_domain = self.domain
            if self.dns_domain is not None:
                self.dns_domain = self.dns_domain.lower()

    controller_ip = ("controller_ip")
    domain = WORDproperty("domain")
    password = textlineproperty("password")
    user = textlineproperty("user")
    wins_ip = textlineproperty("wins_ip")

    def _getWorkgroup(self):
        if not self._workgroup:
            return self.domain.split('.')[0].upper()
        return self._workgroup
    def _setWorkgroup(self, value):
        if value is None:
            value = ''
        self._workgroup = value.strip().upper()
    workgroup = property(fget=_getWorkgroup, fset=_setWorkgroup)

    def isValidWithMsg(self):
        if not self.controller_ip:
            return False, tr("Please specify the authentication server(s).")

        ok, msg = _ad_valid_passwordserver(self.controller_ip)
        if not ok:
            return False, msg

        if not self.domain:
            return False, tr("Please specify the domain name.")

        if not self.user:
            return False, tr("Please specify the user name used to join the domain.")

        if "\\" in self.user:
            return False, tr("Do not specify the domain in the user name.")

        if not self.password:
            return False, tr("Please specify the password used to join the domain.")

        if not check_domain(self.domain):
            return False, tr("Invalid domain.")

        if not check_hostname(self.workgroup):
            return False, tr("Invalid workgroup name.")

        return True, ''

    def getWinsIP(self):
        if self.wins_ip is None or self.wins_ip == '':
            return self.controller_ip
        return self.wins_ip

    @classmethod
    def deserialize(cls, serialized):
        serialized.setdefault('wins_ip', '')
        return cls._deserialize(serialized)

class NndOrg(AbstractOrg):
    DATASTRUCTURE_VERSION = 1
    protocol = NND
    ATTRS = """
        domains
        default_domain
    """.split()

    def __init__(self, domains=None, default_domain=""):
        AbstractOrg.__init__(self)
        if domains is None:
            domains = {}  # key: section_name (e.g. "domain1"), value: NndDomain.
        self._setLocals(locals())

    def isValidWithMsg(self):
        if not self.domains:
            return False, tr("You must add at least one domain.")
        if not self.default_domain:
            return False, tr(
                "You must define a domain as the default domain.")
        realms = {}
        for domain in self.domains.values():
            outcome, error_message = domain.isValidWithMsg()
            if not outcome:
                return outcome, error_message
            try:
                realms[domain.realm.lower()].append(domain.label)
            except KeyError:
                realms[domain.realm.lower()] = [domain.label]
        for realm, domain_labels in realms.items():
            if len(domain_labels) > 1:
                msg = (tr("Error: the following domains have the same realm "
                          '"%s" (whereas realms must be unique):') % realm +
                       " " + ", ".join(sorted(domain_labels)) + ".")
                return False, msg
        return True, ""

class NndDomain(AbstractConf):
    """
    upgrades:
    1 -> 2
    addition of attribute 'user_attr_name'
    """
    DATASTRUCTURE_VERSION = 2
    ATTRS = """
        label
        realm
        type_
        user_attr_name
        user_base_dn
        user_filter
        user_member_attr
        group_attr_name
        group_base_dn
        group_enum_filter
        group_filter
        group_member_attr
        servers
    """.split()
    # type_: "LDAP", "AD" or "edirectory"

    def __init__(self, label="", realm="", type_="LDAP", user_base_dn="",
        user_attr_name="", user_filter="", user_member_attr="",
        group_attr_name="", group_base_dn="", group_enum_filter="",
        group_filter="", group_member_attr="", servers=None):
        self._setLocals(locals())
        AbstractConf.__init__(self)

    def _setservers(self, servers):
        if servers is None:
            servers = []
        self._servers = servers

    def _getservers(self):
        return self._servers

    servers = property(fset=_setservers, fget=_getservers)

    def _settype(self, newtype_):
        self._type_ = newtype_

        if newtype_ == AD:
            supposed_port = 3268
        else:
            supposed_port = None
        for server in self.servers:
            server.supposed_port = supposed_port

    def _gettype(self):
        return self._type_

    type_ = property(fset=_settype, fget=_gettype)

    group_base_dn = dnproperty("group_base_dn")
    user_base_dn = dnproperty("user_base_dn")

    label = textlineproperty("label")
    realm = textlineproperty("realm")
    user_attr_name = textlineproperty("user_attr_name")
    user_filter = textlineproperty("user_filter")
    user_member_attr = textlineproperty("user_member_attr")
    group_attr_name = textlineproperty("group_attr_name")
    group_enum_filter = textlineproperty("group_enum_filter")
    group_filter = textlineproperty("group_filter")
    group_member_attr = textlineproperty("group_member_attr")

    @classmethod
    def checkSerialVersion(cls, serialized):
        datastructure_version = serialized.get('DATASTRUCTURE_VERSION')
        supported_versions = (1, 2,)
        if datastructure_version not in supported_versions:

            #This will raise relevant errors
            cls.raise_version_error(datastructure_version)
        elif datastructure_version < 2:
            #upgrade
            #1 -> 2: add user_attr_name
            serialized['user_attr_name'] = ""
        return datastructure_version

    def downgradeFields(self, serialized, wanted_version):
        if wanted_version == 2:
            return serialized
        if wanted_version == 1:
            # 2 -> 1:
            del serialized['user_attr_name']
            serialized['DATASTRUCTURE_VERSION'] = wanted_version
            return serialized
        raise NotImplementedError()

    def isValidWithMsg(self):
        if not self.label:
            return False, tr("A domain must not have an empty name.")
        if not self.servers:
            return False, tr(
                "You must add at least one server in domain %s.") % self.label
        for server in self.servers:
            outcome, error_message = server.isValidWithMsg()
            if not outcome:
                return outcome, tr("In domain %s:") % self.label + \
                    " " + error_message
        return True, ""


class NndServer(AbstractConf):
    """
    nndserver.supposed_port is None (default value) or an int. It will be used to
    hint valid ldapuris. For instance, a standard ldapuri will use port 389, whereas
    in AD context, the 3268 should be used, and this is the attribute to set this.

    upgrades:
    1 -> 2
    addition of attribute 'user_attr_name'
    """
    DATASTRUCTURE_VERSION = 2
    ATTRS = """
        label
        ldapuri
        bind_dn
        bind_pw
        tls
        checkcert
        ca_cert
        user_attr_name
        user_base_dn
        user_filter
        user_member_attr
        group_attr_name
        group_base_dn
        group_enum_filter
        group_filter
        group_member_attr
    """.split()

    def __init__(self, label="", ldapuri="", bind_dn="", bind_pw="", tls=False,
                 checkcert=False, ca_cert="", user_attr_name="",
                 user_base_dn="", user_filter="", user_member_attr="",
                 group_attr_name="", group_base_dn="", group_enum_filter="",
                 group_filter="", group_member_attr=""):
        AbstractConf.__init__(self)
        self.supposed_port = None
        self._setLocals(locals())

    def has_bind_info(self):
        if self.bind_dn or self.bind_pw:
            return True
        return False

    @classmethod
    def checkSerialVersion(cls, serialized):
        datastructure_version = serialized.get('DATASTRUCTURE_VERSION')
        supported_versions = (1, 2,)
        if datastructure_version not in supported_versions:

            #This will raise relevant errors
            cls.raise_version_error(datastructure_version)
        elif datastructure_version < 2:
            #upgrade
            #1 -> 2: add user_attr_name
            serialized['user_attr_name'] = ""
        return datastructure_version

    def downgradeFields(self, serialized, wanted_version):
        if wanted_version == 2:
            return serialized
        if wanted_version == 1:
            # 2 -> 1:
            del serialized['user_attr_name']
            serialized['DATASTRUCTURE_VERSION'] = wanted_version
            return serialized
        raise NotImplementedError()

    def isValidWithMsg(self):
        if not self.label:
            return False, tr("A server must not have an empty name.")
        if self.checkcert and not self.ca_cert:
            return False, tr('In server %s, "check certificate" is enabled, '
                             'but there is no CA certificate.') % self.label
        if self.tls and has_ldaps(self.ldapuri):
            return False, tr("On server %s, please select either ldaps (in"
                             " the LDAP URI) or the TLS option, but not both.") \
                             % self.label

        return True, ""

    def _setldapuri(self, uri):
        self._ldapuri = cleanuri(uri, default_port=self.supposed_port)

    def _getldapuri(self):
        return self._ldapuri

    ldapuri = property(fset=_setldapuri, fget=_getldapuri)

    bind_dn = dnproperty("bind_dn")
    group_base_dn = dnproperty("group_base_dn")
    user_base_dn = dnproperty("user_base_dn")

    label = textlineproperty("label")
    bind_pw = textlineproperty("bind_pw")
    ca_cert = textlineproperty("ca_cert")
    user_attr_name = textlineproperty("user_attr_name")
    user_filter = textlineproperty("user_filter")
    user_member_attr = textlineproperty("user_member_attr")
    group_attr_name = textlineproperty("group_attr_name")
    group_enum_filter = textlineproperty("group_enum_filter")
    group_filter = textlineproperty("group_filter")
    group_member_attr = textlineproperty("group_member_attr")

    def _set_user_filter(self, ldapfilter):
        """
        a %s is required
        """
        #accept empty value
        if not ldapfilter:
            self._user_filter = ""
            return

        #check other values
        if not "%%s" in ldapfilter:
            raise ValueError(tr("A '%%%%s' is required in user filter - got %s") % ldapfilter)

        self._user_filter = ldapfilter

    def _get_user_filter(self):
        return self._user_filter

    user_filter = property(fset=_set_user_filter, fget=_get_user_filter)


class KerberosAuth(AbstractAuth):
    """
    Configuration for Kerberos.
    """
    # Version 1, attributes: kerberos_domain, kdc, admin_server
    # In version 2, admin_server removed

    ATTRS = """
        kerberos_domain
        kdc
    """.split()

    DATASTRUCTURE_VERSION = 2
    protocol = KERBEROS

    def __init__(self, kerberos_domain=None, kdc=None):
        AbstractAuth.__init__(self)

        #happy pylint
        self.kerberos_domain = self.kdc = None

        self._setLocals(locals())

    def isValidWithMsg(self):
        if not self.kerberos_domain:
            return False, tr("Please specify the Kerberos domain.")

        if not self.kdc:
            return False, tr("Please specify the KDC.")

        return True, ""

    @classmethod
    def checkSerialVersion(cls, serialized):
        datastructure_version = serialized.get('DATASTRUCTURE_VERSION')
        supported_versions = (1, 2)
        if datastructure_version not in supported_versions:
            #This will raise relevant errors
            cls.raise_version_error(datastructure_version)
        else:
            if datastructure_version < 2:
                # Upgrade 1 -> 2:
                if 'admin_server' in serialized:
                    del serialized['admin_server']
        return datastructure_version

    def downgradeFields(self, serialized, wanted_version):
        if wanted_version == 2:
            return serialized
        if wanted_version == 1:
            # 2 -> 1:
            serialized['admin_server'] = serialized['kdc']
            serialized['DATASTRUCTURE_VERSION'] = wanted_version
            return serialized
        raise NotImplementedError()

class KerberosADAuth(AbstractAuth):
    """
    Authentication over kerberos. The kerberos session is opened on the AD server
    """
    DATASTRUCTURE_VERSION = 1
    protocol = KERBEROS_AD

    def isValidWithMsg(self):
        return True, tr("Valid authentication configuration")


