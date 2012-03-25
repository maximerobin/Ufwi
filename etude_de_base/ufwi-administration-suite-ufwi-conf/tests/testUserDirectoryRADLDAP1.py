#coding: utf-8
"""
User Directory test for auth:radius, org:ldap.

Copyright (C) 2009-2011 EdenWall Technologies
Written by Julien Miotte <jmiotte AT edenwall.com>
$Id:$
"""

from templateUserDirectory import templateAuthRad, templateOrgLDAP
from nuconf.common.user_dir import RadiusAuth, LDAPOrg
from nucentral.common.radius_client import RadiusServer

class TestUserDirectoryRADLDAP1(templateAuthRad,
                                templateOrgLDAP):
    """
        Test case : Radius Auth connected to LDAP,
                    LDAP Org (same dir as Auth)
    """

    server = RadiusServer(
                             server=u"172.17.2.1",
                             port=u"1812",
                             secret=u"testing123",
                             timeout=u"1"
                         )
    authConf = RadiusAuth(servers = [server, ])

    user_we_can_test = u"cornelius"
    users_password = u"cornelius"
    orgConf = LDAPOrg(
                        uri = u"ldap://172.17.2.1",
                        dn_users = u"ou=Users,dc=inl,dc=fr",
                        dn_groups = u"ou=Groups,dc=inl,dc=fr",
                        user = u"cn=admin,dc=inl,dc=fr",
                        password = u"INLbabar286",
                        custom_or_nupki = u"SSL_DISABLED",
                        reqcert = u"allow",
                        server_cert_set = False
                     )
    group_of_the_user = u"testeurs"

if __name__ == "__main__":
    choice = raw_input("Calling this file directly will cause application of\n"
                       "the test configuration without reverting it.\n"
                       "You should call it with py.test.\nContinue anyway ? "
                       "[yN] : ")
    if 'y' in choice.strip():
        one_shot = TestUserDirectoryRADLDAP1()
        one_shot.setup_class()
