#coding: utf-8
"""
User Directory test for an AD 2008 (auth:krb-ad, org:ad).

Copyright (C) 2009-2011 EdenWall Technologies
Written by Julien Miotte <jmiotte AT edenwall.com>
$Id:$
"""

from templateUserDirectory import templateOrgAD
from templateUserDirectory import templateAuthKerberosAd
from nuconf.common.user_dir import KerberosADAuth
from nuconf.common.user_dir import ADOrg

class TestUserDirectoryKERBEROSAD2(templateAuthKerberosAd,
                              templateOrgAD):
    """
        Here we test an AD 2008.
    """
    authConf = KerberosADAuth()

    user_we_can_test = "administrator"
    users_password = "1pas2+abc"

    ntp = u"172.17.1.100"
    nameserver = u"172.17.1.100"

    orgConf = ADOrg(
                        controller_ip = "ewfailover.edenwall.com",
                        domain = "EWFAILOVER",
                        dns_domain = "ewfailover.edenwall.com",
                        workgroup = "",
                        user = "Administrator",
                        password = "1pas2+abc",
                        wins_ip = "172.17.1.100"
                   )
    group_of_the_user = "domain users"

if __name__ == "__main__":
    choice = raw_input("Calling this file directly will cause application of\n"
                       "the test configuration without reverting it.\n"
                       "You should call it with py.test.\nContinue anyway ? "
                       "[yN] : ")
    if 'y' in choice.strip():
        one_shot = TestUserDirectoryKERBEROSAD2()
        one_shot.setup_class()
