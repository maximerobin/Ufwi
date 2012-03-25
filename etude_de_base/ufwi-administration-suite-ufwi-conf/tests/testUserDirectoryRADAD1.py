#coding: utf-8
"""
User Directory test for auth:radius, org:ad.

Copyright (C) 2009-2011 EdenWall Technologies
Written by Julien Miotte <jmiotte AT edenwall.com>
$Id:$
"""

from templateUserDirectory import templateAuthRad, templateOrgAD
from nuconf.common.user_dir import RadiusAuth, ADOrg
from nucentral.common.radius_client import RadiusServer

class TestUserDirectoryRADAD1(templateAuthRad,
                              templateOrgAD):
    """
        Test case : Radius Auth connected to LDAP,
                    AD Org
    """

    server = RadiusServer(
                             server=u"172.17.2.1",
                             port=u"1812",
                             secret=u"testing123",
                             timeout=u"1"
                         )
    authConf = RadiusAuth(servers=[server, ])

    user_we_can_test = u"cornelius"
    users_password = u"cornelius"

    ntp = u"172.17.1.1"
    nameserver = u"172.17.1.1"

    orgConf = ADOrg(
                        controller_ip = u"172.17.1.1",
                        domain = u"WIN20030",
                        dns_domain = u"win2003.edenwall.com",
                        workgroup = u"",
                        user = u"Administrator",
                        password = u"1pas2+abc",
                        wins_ip = u"172.17.1.1"
                   )
    group_of_the_user = u"Testers"

if __name__ == "__main__":
    choice = raw_input("Calling this file directly will cause application of\n"
                       "the test configuration without reverting it.\n"
                       "You should call it with py.test.\nContinue anyway ? "
                       "[yN] : ")
    if 'y' in choice.strip():
        one_shot = TestUserDirectoryRADAD1()
        one_shot.setup_class()
