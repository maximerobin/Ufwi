#coding: utf-8
"""
User Directory test for auth:ldap, org:ldap.

Copyright (C) 2009-2011 EdenWall Technologies
Written by Julien Miotte <jmiotte AT edenwall.com>
$Id$
"""

from templateUserDirectory import templateOrgLDAP, templateAuthLDAP
from nuconf.common.user_dir import SameAsOrgAuth, LDAPOrg

class TestUserDirectoryLDAPLDAP1(templateAuthLDAP,
                                 templateOrgLDAP):
    """
        Test case : LDAP Auth connected to LDAP,
                    LDAP Org (same dir as Auth)
    """

    authConf = SameAsOrgAuth()
    user_we_can_test = "Administrateur"
    users_password = "cornelius"
    orgConf = LDAPOrg(
                        uri = "ldap://172.17.2.1",
                        dn_users = "ou=Users,dc=inl,dc=fr",
                        dn_groups = "ou=Groups,dc=inl,dc=fr",
                        user = "cn=admin,dc=inl,dc=fr",
                        password = "INLbabar286",
                        custom_or_nupki = "SSL_DISABLED",
                        reqcert = "allow",
                        server_cert_set = False
                     )
    group_of_the_user = "testeurs"

if __name__ == "__main__":
    choice = raw_input("Calling this file directly will cause application of\n"
                       "the test configuration without reverting it.\n"
                       "You should call it with py.test.\nContinue anyway ? "
                       "[yN] : ")
    if 'y' in choice.strip():
        one_shot = TestUserDirectoryLDAPLDAP1()
        one_shot.setup_class()
