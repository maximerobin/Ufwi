#coding: utf-8
"""
User Directory test for an AD 2008 R2 (auth:krb, org:ad).

Copyright (C) 2009-2011 EdenWall Technologies
Written by Julien Miotte <jmiotte AT edenwall.com>
"""

from templateUserDirectory import templateAuthKerberosOrgAd
from nuconf.common.user_dir import KerberosAuth
from nuconf.common.user_dir import ADOrg

class TestUserDirectoryKerberos_keytab(templateAuthKerberosOrgAd):
    """
        Here we test an AD 2008 R2, and we're specifying the kerberos server
        manually.
    """
    user_we_can_test = "administrator"
    users_password = "1pas2+abc"

    ntp = u"172.17.1.4"
    nameserver = u"172.17.1.4"
    keytab = "keytab-test"
    hostname = "amstrad"

    authConf = KerberosAuth(kerberos_domain="WIN2008R2", kdc="172.17.1.4")

    orgConf = ADOrg(
                        controller_ip = "win2008r2.edenwall.com",
                        domain = "win2008r2.edenwall.com",
                        dns_domain = "",
                        workgroup = "",
                        user = "Administrator",
                        password = "1pas2+abc",
                        wins_ip = "172.17.1.4"
                   )
    group_of_the_user = "domain users"

    keytab = "keytab-test"

if __name__ == "__main__":
    choice = raw_input("Calling this file directly will cause application of\n"
                       "the test configuration without reverting it.\n"
                       "You should call it with py.test.\nContinue anyway ? "
                       "[yN] : ")
    if 'y' in choice.strip():
        one_shot = TestUserDirectoryKerberos_keytab()
        one_shot.setup_class()
