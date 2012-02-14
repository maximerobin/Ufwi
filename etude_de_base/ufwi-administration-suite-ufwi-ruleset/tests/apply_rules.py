#!/usr/bin/env python
"""
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

from __future__ import with_statement

import sys
from copy import deepcopy
from difflib import context_diff
from os.path import dirname, join as path_join, basename, exists
from os import rename, unlink
from optparse import OptionParser
from shutil import copyfile
from logging import basicConfig, CRITICAL
from glob import glob

from ufwi_ruleset.config import RULESET_DIR
from ufwi_ruleset.common.parameters import NUFW_GATEWAY
from ufwi_rpcd.client import RpcdClientBase
# from ufwi_conf.common.netcfg_rw import deserialize
from ufwi_rpcd.client.error import RpcdError

class RunTests:
    def __init__(self):
        self.parseOptions()
        self.setupLog()

        cwd = dirname(__file__)
        parent_dir = path_join(cwd, '..')
        sys.path.insert(0, parent_dir)
        self.directory = path_join(cwd, "rulesets")

    def parseOptions(self):
        parser = OptionParser(usage="%prog [options] [test1 test2 ...]")
        parser.add_option("--regenerate", help="Regenerate tests instead of testing",
            action="store_true", default=False)
        parser.add_option("-x", "--exitfirst", help="Exit on first error",
            action="store_true", default=False)
        parser.add_option("-r", "--rulesets", help="Exit on first error",
            action="store", default="")
        self.options, unused = parser.parse_args()

    def setupLog(self):
        basicConfig(level=CRITICAL)

    def createRules(self, source):
        ruleset_filename = path_join(RULESET_DIR, "rulesets", "test.xml")
        old_ruleset_filename = ruleset_filename + ".old"
        local_ipv4 = path_join(RULESET_DIR, 'local_rules_ipv4.d')
        local_ipv4_tmp = local_ipv4 + '.tmp'
        if exists(old_ruleset_filename):
            raise Exception("%s already exists!" % old_ruleset_filename)
        if exists(local_ipv4_tmp):
            raise Exception("%s already exists!" % local_ipv4_tmp)

        rules = {}

        try:
            rename(ruleset_filename, old_ruleset_filename)
        except OSError:
            old_ruleset_filename = None

        try:
            copyfile(source, ruleset_filename)
            self.client.call('ufwi_ruleset', 'rulesetOpen', 'ruleset', "test")
            rename(local_ipv4, local_ipv4_tmp)
            try:
                result = self.client.call('ufwi_ruleset', 'applyRules', False, True)
                if not result['applied']:
                    errors = '\n'.join(result['errors'])
                    raise Exception("Apply errors:\n%s" % errors)

                result = self.client.call('ufwi_ruleset', 'ldapRules', 'acls-ipv4', tuple())
                rules['ldap_ipv4'] = result['ldap']

                result = self.client.call('ufwi_ruleset', 'ldapRules', 'acls-ipv6', tuple())
                rules['ldap_ipv6'] = result['ldap']
            finally:
                rename(local_ipv4_tmp, local_ipv4)
        finally:
            if old_ruleset_filename:
                rename(old_ruleset_filename, ruleset_filename)
        self.client.call('ufwi_ruleset', 'rulesetClose')

        for key, filename in (
        ('iptables_ipv4', 'new_rules_ipv4'),
        ('iptables_ipv6', 'new_rules_ipv6')):
            with open(path_join(RULESET_DIR, filename)) as fp:
                lines = [line.rstrip() for line in fp]
                # ignore the header and footer:
                # - first line contains version and timestamp
                # - last line contains a timestamp
                rules[key] = lines[1:-1]
        return rules

    def checkRules(self, source, key, ufwi_ruleset):
        # bart.xml => bart.iptables_ipv4
        correct = source[:-3] + key
        prefix = "%s:%s" % (basename(source)[:-4], key)

        if self.options.regenerate:
            if ufwi_ruleset:
                print "%s: file regenerated" % prefix
                with open(correct, "w") as fp:
                    for line in ufwi_ruleset:
                        print >>fp, line
            elif exists(correct):
                print "%s: remove file (no rule)" % prefix
                unlink(correct)
            return True

        text1 = ufwi_ruleset
        if exists(correct):
            with open(correct) as fp:
                text2 = [line.rstrip() for line in fp]
        else:
            text2 = tuple()
        diff = list(context_diff(text1, text2))
        if diff:
            print "%s: FAILURE!" % prefix
            for line in diff:
                print line.rstrip()
            return False
        print "%s: ok" % prefix
        return True

    def main(self):
        """return True if all tests are successful"""
        self.client = RpcdClientBase(protocol="http", host="localhost")
        try:
            self.client.authenticate('admin', 'admin')

            self.configureNetwork()

            old_config = self.client.call('ufwi_ruleset', 'getConfig')
            new_config = deepcopy(old_config)
            new_config['global']['firewall_type'] = NUFW_GATEWAY
            new_config['iptables']['log_type'] = 'ULOG'

            try:
                self.client.call('ufwi_ruleset', 'setConfig', new_config)

                failures = 0
                if self.options.rulesets:
                    rulesets = [
                        (path_join(self.directory, ruleset) + ".xml")
                        for ruleset in self.rulesets]
                else:
                    rulesets = glob(path_join(self.directory, "*.xml"))

                print "Rulesets:", rulesets
                for ruleset in rulesets:
                    ok = self.testRuleset(ruleset)
                    if not ok:
                        failures += 1
                        if self.options.exitfirst:
                            break

                if failures:
                    print "%s failures!" % failures
                    return False
            finally:
                self.client.call('ufwi_ruleset', 'setConfig', old_config)
        finally:
            self.client.logout()

        return True

    def testRuleset(self, ruleset):
        print "Test %s" % basename(ruleset)
        rules = self.createRules(ruleset)
        ok = True
        for key in rules:
            ok &= self.checkRules(ruleset, key, rules[key])
            if not ok and self.options.exitfirst:
                break
        return ok

    def configureNetwork(self):
        """
            Custom network configuration
        """
        serialized = self.client.call('network', 'getNetconfig')
        print serialized
        # serialized =
        # self.takeNuconfWriteRole()
        # self.client.call('network', 'setNetconfig', serialized)
        # self.client.call('config', 'apply')

    def takeNuconfWriteRole(self):
        """
            Takes the ufwi_conf_write role
        """
        try:
            self.client.call("session", "acquire", "ufwi_conf_write")
        except RpcdError:
            pass
        try:
            self.client.call("ufwi_conf", "takeWriteRole")
        except RpcdError:
            pass


if __name__ == "__main__":
    assert RunTests().main()

