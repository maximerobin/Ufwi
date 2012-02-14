#coding: utf-8
"""
User Directory test for an AD 2008 R2 (auth:krb-ad, org:ad).

Copyright (C) 2009-2011 EdenWall Technologies
Written by Julien Miotte <jmiotte AT edenwall.com>
$Id:$
"""

from templateUserDirectory import templateOrgAD
from templateUserDirectory import templateAuthKerberosAd
from nuconf.common.user_dir import KerberosADAuth
from nuconf.common.user_dir import ADOrg

class TestUserDirectoryKERBEROSAD3(templateAuthKerberosAd,
                              templateOrgAD):
    """
        Here we test an AD 2008R2
    """
    authConf = KerberosADAuth()

    user_we_can_test = "cornelius"
    users_password = "1pas2+abc"

    ntp = u"172.17.1.4"
    nameserver = u"172.17.1.4"

    orgConf = ADOrg(
                        controller_ip = "win2008r2.edenwall.com",
                        domain = "WIN2008R2",
                        dns_domain = "win2008r2.edenwall.com",
                        workgroup = "",
                        user = "Administrator",
                        password = "1pas2+abc",
                        wins_ip = "172.17.1.4"
                   )
    group_of_the_user = "domain users"

if __name__ == "__main__":
    choice = raw_input("Calling this file directly will cause application of\n"
                       "the test configuration without reverting it.\n"
                       "You should call it with py.test.\nContinue anyway ? "
                       "[yN] : ")
    if 'y' in choice.strip():
        one_shot = TestUserDirectoryKERBEROSAD3()
        one_shot.setup_class()
