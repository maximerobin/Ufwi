#coding: utf-8
"""
User Directory test for an AD 2003 (auth:krb, org:ad).

Copyright (C) 2009-2011 EdenWall Technologies
Written by Julien Miotte <jmiotte AT edenwall.com>
$Id:$
"""

from templateUserDirectory import templateOrgAD
from templateUserDirectory import templateAuthKerberosAd
from nuconf.common.user_dir import KerberosADAuth
from nuconf.common.user_dir import ADOrg

class TestUserDirectoryKERBEROSAD1(templateAuthKerberosAd,
                                   templateOrgAD):
    """
        Here we test an AD 2003.
    """
    authConf = KerberosADAuth()

    user_we_can_test = u"cornelius"
    users_password = u"1pas2+abc"

    ntp = u"172.17.1.1"
    nameserver = u"172.17.1.1"
    hostname = ""

    orgConf = ADOrg(
                        controller_ip = u"win2003.edenwall.com",
                        domain = u"WIN20030",
                        dns_domain = u"win2003.edenwall.com",
                        workgroup = u"",
                        user = u"Administrator",
                        password = u"1pas2+abc",
                        wins_ip = u"172.17.1.1"
                   )
    group_of_the_user = u"172.17.1.1"

if __name__ == "__main__":
    choice = raw_input("Calling this file directly will cause application of\n"
                       "the test configuration without reverting it.\n"
                       "You should call it with py.test.\nContinue anyway ? "
                       "[yN] : ")
    if 'y' in choice.strip():
        one_shot = TestUserDirectoryKERBEROSAD1()
        one_shot.setup_class()
