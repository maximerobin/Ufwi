#coding: utf-8
"""
User Directory test for an AD 2008 R2 (auth:krb, org:nnd).

Copyright (C) 2009-2011 EdenWall Technologies
Written by Julien Miotte <jmiotte AT edenwall.com>
"""

from templateUserDirectory import templateAuthKerberosOrgNND
from nuconf.common.user_dir import KerberosAuth
from nuconf.common.user_dir import NndOrg

class TestUserDirectoryKerberos_NND(templateAuthKerberosOrgNND):
    """
        Testing an win2008r2 AD with NND, and we're specifying the kerberos
        server and keytab manually.
    """
    user_we_can_test = "administrator"
    users_password = "1pas2+abc"

    ntp = u"172.17.1.4"
    nameserver = u"172.17.1.4"
    keytab = "keytab-test"
    hostname = "amstrad"

    authConf = KerberosAuth(kerberos_domain="win2008r2.edenwall.com", kdc="win2008r2.edenwall.com")

    orgConf = NndOrg.deserialize({
         'DATASTRUCTURE_VERSION': 1,
         '__type__': 'nuconf.common.user_dir.base.NndOrg',
         'default_domain': 'win2008r2.edenwall.com',
         'domains': {
                '__type__': 'dict',
                'win2008r2.edenwall.com': {
                        'DATASTRUCTURE_VERSION': 2,
                        '__type__': 'nuconf.common.user_dir.base.NndDomain',
                        'group_attr_name': 'cn',
                        'group_base_dn': 'cn=users,dc=win2008r2,dc=edenwall,dc=com',
                        'group_enum_filter': 'objectClass=group',
                        'group_filter': 'cn=%%s',
                        'group_member_attr': '',
                        'label': 'win2008r2.edenwall.com',
                        'realm': 'win2008r2.edenwall.com',
                        'servers': {'0': {'DATASTRUCTURE_VERSION': 2,
                                          '__type__': 'nuconf.common.user_dir.base.NndServer',
                                          'bind_dn': 'cn=administrator,cn=users,dc=win2008r2,dc=edenwall,dc=com ',
                                          'bind_pw': '1pas2+abc',
                                          'ca_cert': '',
                                          'checkcert': False,
                                          'group_attr_name': '',
                                          'group_base_dn': '',
                                          'group_enum_filter': '',
                                          'group_filter': '',
                                          'group_member_attr': '',
                                          'label': 'ldap://172.17.1.4:3268',
                                          'ldapuri': 'ldap://172.17.1.4:3268',
                                          'tls': False,
                                          'user_attr_name': '',
                                          'user_base_dn': '',
                                          'user_filter': '',
                                          'user_member_attr': ''},
                                    '__type__': 'list'},
                        'type_': 'AD',
                        'user_attr_name': '',
                        'user_base_dn': 'cn=users,dc=win2008r2,dc=edenwall,dc=com',
                        'user_filter': 'sAMAccountName=%%s',
                        'user_member_attr': 'memberOf'
                        }
                    }
    })

    group_of_the_user = "domain users"

    keytab = "keytab-test"

if __name__ == "__main__":
    pass

