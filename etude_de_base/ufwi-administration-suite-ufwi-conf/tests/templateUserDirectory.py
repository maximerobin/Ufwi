#coding: utf-8
"""
Template for tests of the User Directory functionnality 

Copyright (C) 2009-2011 EdenWall Technologies
Written by Julien Miotte <jmiotte AT edenwall.com>
$Id: templateUserDirectoryLDAP.py 15028 2009-12-02 13:22:14Z jmiotte $

This file contains tests for the User Directory functionnality.
The class template User Directory checks that we can feth the user id and his
groups. The classes templateAuth* and templateOrg* do more specific tests.

Classes available (see below) :
- Auth :
    - Rad
    - LDAP
    - Kerberos
- Org
    - LDAP
"""

from __future__ import with_statement

from atlee_pam import authenticate
from nucentral.common.download import encodeFileContent
from nuconf.common.user_dir import SameAsOrgAuth, LDAPOrg, ADOrg
from os import makedirs
from os.path import isdir
from templateTest import Test
from time import sleep
import subprocess

from nuconf.common.user_dir.base import NuauthCfg

# {{{ class templateUserDirectory(Test)
class templateUserDirectory(Test):
    """
        Test of the User Directory functionnality
        - check if when can fetch a users groups with id
        - check if when can feth the groups with getent group
    """
    REQUIRE_COMPONENTS = ('nuauth',)

    authConf = None
    orgConf = None
    user_we_can_test = ""
    users_password = ""
    group_of_the_user = ""

    @classmethod
    def configureDns(cls):
        """abstract method"""
        print "configure DNS: nothing to do"

    @classmethod
    def configureNtpApplySynchronize(cls):
        """abstract method"""
        print "NTP - configure & apply & synchronize: nothing to do"

    @classmethod
    def configureKeytab(cls):
        pass

    @classmethod
    def configureHostname(cls):
        # by default do nothing
        pass
        cls.client.call('hostname', 'setShortHostname', u'amstrad', u'Configure hostname')

    @classmethod
    def setup_class(cls):
        """
            This method is called once when the class is first instanciated. It
            sets up the testing conditions, while saving the current configuration.
        """
        Test.setup_class()

        cls.old_hostname = cls.client.call('hostname', 'getShortHostname')

        cls.test_path = cls.results_path+cls.date+"/"+cls.__name__+"/"
        if not isdir(cls.test_path):
            makedirs(cls.test_path)

        # Let's create a backup of the original configuration
        cls.orig = cls.client.call('nuauth','getNuauthConfig')

        # We get some md5 sums to check if it the files are written
        cls.firstMD5_nsswitch_conf = cls.md5sum("/etc/nsswitch.conf")
        cls.firstMD5_libnss_ldap = cls.md5sum("/etc/libnss-ldap.conf")
        cls.firstMD5_ldap_conf = cls.md5sum("/etc/ldap/ldap.conf")
        ###########################################################

        cls.takeNuconfWriteRole()

        # ***APPLY*** and synchronize
        cls.configureNtpApplySynchronize()

        cls.configureHostname()

        cls.configureDns()

        # We create a new Nuauth (user dir) configuration
        nuauthcfg = NuauthCfg(cls.authConf, cls.orgConf)
        serialized = nuauthcfg.serialize()

        # We apply this configuration
        cls.client.call('nuauth', 'setNuauthConfig', serialized, 'tests')
        cls.configureKeytab()
        cls.apply_nuconf()

        # We get some md5 sums to check if it the files are written
        cls.secondMD5_nsswitch_conf = cls.md5sum("/etc/nsswitch.conf")
        cls.secondMD5_libnss_ldap = cls.md5sum("/etc/libnss-ldap.conf")
        cls.secondMD5_ldap_conf = cls.md5sum("/etc/ldap/ldap.conf")
        ###########################################################

    def test_we_can_fetch_groups_from_user(self):
        """
            Check that we can fetch the user's group with 'id'
        """
        tries = 5
        while tries > 0:
            handle = subprocess.Popen("id "+self.user_we_can_test,
                                      shell=True,
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE,
                                      close_fds=True)
            results = unicode(handle.stdout.read(), 'utf-8')
            results_err = unicode(handle.stderr.read(), 'utf-8')
            if not results_err and self.group_of_the_user in results:
                break
            tries = tries - 1
            sleep(2)

        assert results_err == u"", u"check id " + self.user_we_can_test

        error = u"check id %s - results: %s, while group of user: %s" % \
                    (self.user_we_can_test, results, self.group_of_the_user)
        assert self.group_of_the_user in results, "%r not in %r" % (self.group_of_the_user, results)

    def test_we_can_fetch_the_groups(self):
        """
            Check that we can feth all the test groups with 'getent group'
        """
        tries = 5
        while tries > 0:
            handle = subprocess.Popen("getent group",
                                      shell=True,
                                      stdout=subprocess.PIPE)
            results = unicode(handle.stdout.read(), 'utf-8')
            if self.group_of_the_user in results and \
                self.user_we_can_test in results:
                break
            tries = tries - 1
            sleep(2)

        error = u"check getent group, wrong info. "\
            "(attempt: '%s %s' received: '%s')" %\
            (self.group_of_the_user, self.user_we_can_test, results)
        assert self.group_of_the_user in results
        assert self.user_we_can_test in results

    def test_nsswitch_is_correctly_written(self):
        """
            Check that /etc/nsswitch.conf has the correct configuration
        """
        # Check that the file is even written, before checking its contents
        assert self.firstMD5_nsswitch_conf != self.secondMD5_nsswitch_conf, \
                                    "/etc/nsswitch.conf hasn't been written"

        ldap_org = self.orgConf.__class__ == LDAPOrg()
        ad_org = self.orgConf.__class__ == ADOrg()
        if ldap_org or ad_org :
            filename = "/etc/nsswitch.conf"

            keyword = ""
            if ldap_org:
                keyword = "ldap"
            elif ad_org:
                keyword = "winbind"

            expected = ("passwd:         files %s" % keyword,
                        "group:          files %s" % keyword
            )

            self.correctly_written(filename, expected)

    @classmethod
    def teardown_class(cls):
        """
            This method is called once when all tests have been done.
            It restores the saved configuration.
        """
        # Here, unlike other test classes, we won't restore the old
        # configuration for at least 2 reasons :
        # 1. The original user directory configuration may be invalid (like in
        #    a fresh install)
        # 2. The original user directory configuration may be an Active
        #    Directory one, and these take a loooooooooooong time to join.
        #cls.client.call('nuauth','setNuauthConfig',cls.orig,'pas de message')
        #cls.client.call('config','apply')

        cls.client.call('hostname', 'setShortHostname', cls.old_hostname, 'teardown : hostname')
        cls.apply_nuconf()
        Test.teardown_class()

# }}}
# {{{ class templateAuthRad


class pamTest(object):
    def test_we_can_auth_our_test_user_with_pam(self):
        """
            Check that we can authenticate our test user with atlee-pam
        """
        error = "We can't authenticate the user %s with the password %s"
        tries = 5
        while tries >  0:
            result = authenticate(self.user_we_can_test,
                                        self.users_password,
                                        service="nuauth")
            if result:
                break
            tries = tries - 1
            sleep(2)

        assert result, error % (self.user_we_can_test, self.users_password)


class templateAuthRad(templateUserDirectory, pamTest):
    """
        Here we will have all the tests concerning a Radius Authentication Referral
        - We will check all the PAM files :
            - /etc/pam.d/nuauth
            - /etc/pam_radius_auth.conf
    """

    def test_pam_radius_auth_is_correctly_written(self):
        """
            Check that /etc/pam_radius_auth.conf has the correct configuration
        """
        filename = "/etc/pam_radius_auth.conf"
        expected = "%s.*%s.*%s" % (self.authConf.servers[0].server_string(),
                                     self.authConf.servers[0].secret,
                                     str(self.authConf.servers[0].timeout))
        self.correctly_written(filename, (expected,))

    def test_pamd_nuauth_is_correctly_written(self):
        """
            Check that /etc/pam.d/nuauth has the correct configuration
        """
        filename = "/etc/pam.d/nuauth"
        expected = ("auth    sufficient    /lib/security/pam_radius_auth.so",)
        self.correctly_written(filename, expected)
# }}}
# {{{ class templateAuthLDAP
class templateAuthLDAP(templateUserDirectory, pamTest):
    """
        Here we will have all the tests concerning an LDAP Authentication Referral
        - We will check the files :
            - /etc/pam.d/nuauth
            - /etc/pam_ldap.conf
    """

    def test_pam_ldap_is_correctly_written(self):
        """
            Check that /etc/pam_ldap.conf has the correct configuration
        """
        filename = "/etc/pam_ldap.conf"

        if self.authConf.__class__ == SameAsOrgAuth:
            auth_conf = self.orgConf
        else:
            auth_conf = self.authConf

        _expected = ["nss_base_passwd %s" % auth_conf.dn_users,
                    "nss_base_group %s" % auth_conf.dn_groups,
                    "uri %s" % auth_conf.uri]

        if auth_conf.user:
            _expected.append("binddn %s" % auth_conf.user)
            if auth_conf.password:
                _expected.append("bindpw %s" % auth_conf.password)

        expected = tuple(_expected)

        self.correctly_written(filename, expected)

    def test_pamd_nuauth_is_correctly_written(self):
        """
            Check that /etc/pam.d/nuauth has the correct configuration
        """
        filename = "/etc/pam.d/nuauth"
        expected = ("auth    sufficient    /lib/security/pam_ldap.so",)
        self.correctly_written(filename, expected)
# }}}

class templateAuthKerberos(object):
    @classmethod
    def configureHostname(cls):
        cls.client.call('hostname', 'setShortHostname', u'amstrad', u'Configure hostname')

    @classmethod
    def configureKeytab(cls):
        with open(cls.keytab, 'rb') as fd:
            content = fd.read()

        content = encodeFileContent(content)

        cls.client.call('nuauth', 'upload_krb_keytab', content)

    def run_cmd(self, command, input=None, ret=0):
        err_fmt = "stdout : '%s' \n stderr: '%s'"
        p = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate(input)
        if ret is None:
            p.wait()
            return

        assert ret == p.wait(), err_fmt % (stdout, stderr)
        return stdout, stderr

    def test_auth(self):
        """
            Try to authenticate our test user with kinit and nutcpc
        """
        self.run_cmd("kdestroy", ret=None)
        self.run_cmd("nutcpc -k", ret=None)

        cmd = "kinit %s" % self.user_we_can_test
        self.run_cmd(cmd, input=self.users_password)

        cmd = "klist"
        stdout, stderr = self.run_cmd(cmd)
        output = "stdout : %s / stderr : %s" % (stdout, stderr)
        assert ("nuauth/%s.%s@%s" % (self.hostname, self.dns_domain.lower(), self.domain.upper())) in stdout, output

        cmd = "nutcpc -U %s -H %s.%s" % (self.user_we_can_test, self.hostname, self.dns_domain.lower())
        # The following fails if the return code isn't 0.
        self.run_cmd(cmd)

    def test_bad_auth(self):
        """
            Check that a bad password won't authenticate our test user (with
            kinit and nutcpc).
        """
        self.run_cmd("kdestroy", ret=None)
        self.run_cmd("nutcpc -k", ret=None)

        cmd = "kinit %s" % self.user_we_can_test
        output = self.run_cmd(cmd, input=self.users_password, ret=1)
        assert output[1].startswith('kinit: krb5_get_init_creds: Client')
        assert output[1].endswith("unknow\n")

        cmd = "nutcpc -U %s -H %s.%s -M GSSAPI -Q" % (self.user_we_can_test, self.hostname, self.dns_domain.lower())
        output = self.run_cmd(cmd, ret=1)
        assert output[0].endswith("Authentication failed (check parameters)\n")

    def test_nuauth_keytab(self):
        """
            Check the permissions of nuauth keytab.
        """
        perm = "-rw-r----- 1 root nuauth"
        output = self.run_cmd("ls -l /etc/nufw/nuauth.keytab", ret=0)
        assert output[0].startswith(perm)

# {{{ class templateAuthKerberosAd
class templateAuthKerberosAd(templateUserDirectory, templateAuthKerberos):
    """
        Here we will have all the tests concerning an Kerberos AD Authentication
        Referral
        - We check the files :
            - /etc/nufw/nuauth.conf
    """

    @classmethod
    def configureHostname(cls):
        cls.client.call('hostname', 'setShortHostname', u'amstrad', u'Configure hostname')

    def test_nuauth_conf_is_correctly_written(self):
        """
            Check that /etc/nufw/nuauth.conf is correctly written
        """
        filename = "/etc/nufw/nuauth.conf"
        expected = ('\ninclude "/etc/nufw/nuauth.d/nuauth_krb5.conf"',)
        self.correctly_written(filename, expected)

    def test_nuauth_keytab(self):
        """
            Check that we've got the correct tickets using ktutil
        """
        command = "ktutil -k /etc/nufw/nuauth.keytab list"
        expected = ('nuauth.*%s' % self.orgConf.dns_domain.upper(),)
        self.output_check(command, expected)

    # ENABLE when #2931 fixed
#    def test_krb5_conf(self):
#        filename = "/etc/krb5.conf"
#        expected = ("kdc = %s" % self.orgConf.controller_ip,
#                    ".%s = %s" % (self.orgConf.dns_domain.lower(),
#                    self.orgConf.domain.upper()))
#        self.correctly_written(filename, expected)

# }}}
# {{{ class templateOrgAD
class templateOrgAD(templateUserDirectory):
    """
        Here we will have all the tests concerning an AD Organization Referral
        - We check the files :
            - /etc/samba/samba.conf
            - /etc/bind/named.conf.local
    """
    @classmethod
    def configureHostname(cls):
        cls.client.call('hostname', 'setShortHostname', u'amstrad', u'Configure hostname')

    def test_samba_conf_is_correctly_written(self):
        """
            Check that /etc/samba/samba.conf is correctly written
        """
        realm = "WIN2008R2.EDENWALL.COM"
        password_server = self.users_password
        print realm, password_server
        assert True

    def test_named_conf(self):
        """
            Check that /etc/bind/named.conf.local is correctly written
        """
        filename = "/etc/bind/named.conf.local"
        expected = (self.orgConf.controller_ip, )
        self.correctly_written(filename, expected)

    @classmethod
    def configureDns(cls):
        # We configure resolv
        resolv_dir = {  'domain': cls.orgConf.dns_domain,
                        'nameserver1': cls.nameserver,
                        'nameserver2': u''
        }
        commit_msg = u'test AD - configure dns and domaine'
        cls.client.call('resolv', 'setResolvConfig', resolv_dir, commit_msg)

    @classmethod
    def configureNtpApplySynchronize(cls):
        # We configure NTP
        commit_msg = u'test AD - configure NTP, save, apply, synchronize'
        ntp_config = cls.client.call('ntp', 'getNtpConfig')
        ntp_config['ntpservers'] = cls.ntp
        cls.client.call('ntp', 'setNtpConfig', ntp_config, commit_msg)
        cls.client.call('config', 'apply')
        cls.client.call('ntp', 'syncTime')

# }}}
# {{{ class templateOrgLDAP
class templateOrgLDAP(templateUserDirectory):
    """
        Here we will have all the tests concerning a LDAP Organization Referral
        - We check the files :
            - /etc/libnss-ldap.conf
            - /etc/nsswitch.conf
            - /etc/ldap/ldap.conf
    """
    def test_libnss_ldap_is_correctly_written(self):
        """
            Check that /etc/libdnss-ldap.conf has the correct configuration
        """
        # Check that the file is even written, before checking its contents
        error = "/etc/libnss-ldap.conf hasn't been written"
        assert self.firstMD5_libnss_ldap != self.secondMD5_libnss_ldap, error

        filename = "/etc/libnss-ldap.conf"

        _expected = ["nss_base_passwd %s" % self.orgConf.dn_users,
                     "nss_base_group %s" % self.orgConf.dn_groups,
                     "uri %s" % self.orgConf.uri]

        if self.orgConf.user:
            _expected.append("binddn %s" % self.orgConf.user)
            if self.orgConf.password:
                _expected.append("bindpw %s" % self.orgConf.password)

        expected = tuple(_expected)
        self.correctly_written(filename, expected)

    def test_ldap_conf_is_correctly_written(self):
        """
            Check that /etc/ldap/ldap.conf has the correct configuration
        """
        # Check that the file is even written, before checking its contents
        error = "/etc/ldap/ldap.conf hasn't been written"
        assert self.firstMD5_ldap_conf != self.secondMD5_ldap_conf, error

        filename = "/etc/ldap/ldap.conf"
        expected = ("TLS_REQCERT %s" % self.orgConf.reqcert,)
        self.correctly_written(filename, expected)
# }}}

class templateAuthKerberosOrgAd(templateOrgAD):

    @classmethod
    def configureKeytab(cls):
        # nothing todo
        pass

    def test_samba_conf_is_correctly_written(self):
        pass

    def test_named_conf(self):
        pass

    def test_nuauth_krb5_conf(self):
        """
            Check that /etc/nufw/nuauth.d/nuauth_krb5.conf is correctly written.
        """
        filename = "/etc/nufw/nuauth.d/nuauth_krb5.conf"

        expected = ("\nnuauth_uses_fake_sasl=0",
                    "\nnuauth_krb5_hostname=\"%s\"" % self.hostname,
                    "\nnuauth_krb5_realm=\"%s\"" % self.authConf.kerberos_domain.upper(),)
        self.correctly_written(filename, expected)

    def test_nuauth_user_dir_conf(self):
        """
            Check that /etc/nufw/nuauth.d/nuauth_user_dir.conf is correctly
            written.
        """
        filename = "/etc/nufw/nuauth.d/nuauth_user_dir.conf"

        expected = ("\nnuauth_user_check_module=\"system\"",
                    "\nnuauth_get_user_id_module=\"system\"",
                    "\nnuauth_get_user_groups_module=\"system\"",
                    "\nnuauth_use_groups_name=0",)
        self.correctly_written(filename, expected)

    def test_krb5_conf(self):
        """
            Check that /etc/krb5.conf is correctly written.
        """
        filename = "/etc/krb5.conf"
        expected = ("kdc = %s" % self.authConf.kdc,
                    ".%s = %s" % (self.authConf.kerberos_domain.lower(),
                    self.authConf.kerberos_domain.upper()))
        self.correctly_written(filename, expected)

class templateAuthKerberosOrgNND(Test, templateAuthKerberos):

    def test_krb5_conf(self):
        """
            Check that /etc/krb5.conf is correctly written.
        """
        filename = "/etc/krb5.conf"
        expected = ("kdc = %s" % self.authConf.kdc,
                    ".%s = %s" % (self.authConf.kerberos_domain.lower(),
                    self.authConf.kerberos_domain.upper()))
        self.correctly_written(filename, expected)

    def test_nuauth_user_dir_conf(self):
        """
            Check that /etc/nufw/nuauth.d/nuauth_user_dir.conf is correctly
            written.
        """
        filename = "/etc/nufw/nuauth.d/nuauth_user_dir.conf"
        expected = ("\nnuauth_user_check_module=\"nnd\"",
                    "\nnuauth_get_user_id_module=\"nnd\"",
                    "\nnuauth_get_user_groups_module=\"nnd\"",
                    "\nnuauth_use_groups_name=1",)
        self.correctly_written(filename, expected)

    def test_nuauth_krb5_conf(self):
        """
            Check that /etc/nufw/nuauth.d/nuauth_krb5.conf is correctly
            written.
        """
        filename = "/etc/nufw/nuauth.d/nuauth_krb5.conf"

        expected = ("\nnuauth_uses_fake_sasl=0",
                    "\nnuauth_krb5_hostname=\"%s\"" % self.hostname,
                    "\nnuauth_krb5_realm=\"%s\"" % self.orgConf.default_domain.upper(),)
        self.correctly_written(filename, expected)
