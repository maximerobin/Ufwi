#coding: utf-8
"""
Template config test file, checking the consistency of the config module.

Copyright (C) 2009-2011 EdenWall Technologies
Written by Julien Miotte <jmiotte AT edenwall.com>
$Id: testBonding.py 19604 2010-04-19 12:56:19Z lds $
"""

#from ldap import initialize, SCOPE_SUBTREE
from __future__ import with_statement
#from nuconf.common.netcfg_rw import deserialize
#from nuconf.common.net_objects_rw import NetRW
#from copy import deepcopy
#from IPy import IP
from templateTest import Test
from os import makedirs
from os.path import isdir, exists
from subprocess import Popen, PIPE
from nucentral.common.download import encodeFileContent
from py import test
import re

SAVED = "/var/lib/nucentral/versionned/configuration/saved-configuration.xml"
DIFF = "/var/lib/nucentral/versionned/configuration/saved_diff-configuration.xml"
RUNNING = "/var/lib/nucentral/versionned/configuration/configuration.xml"
LAST_WORKING = "/var/lib/nucentral/versionned/configuration/last_working-configuration.xml"
NTP = "/etc/ntp.conf"


class templateConfig(Test):
    to_save_ip = ""
    saved_ip = ""
    applied_ip = ""
    next_apply_restore = False
    with_ha = False

    @classmethod
    def setup_class(cls, with_ha=False):
        """
            This method is called once when the class is first instanciated. It
            sets up the testing conditions, while saving the current configuration.
        """
        Test.setup_class()

        cls.test_path = cls.results_path+cls.date+"/TestConfig/"
        if not isdir(cls.test_path):
            makedirs(cls.test_path)

        cls.with_ha = with_ha

        cls.local_ha_state = cls.client.call("ha", "getState")[0]
        if cls.local_ha_state != "CONNECTED" and with_ha:
            test.skip("!! Are you mad ? You're trying to do a HA test without being actually connected (local state is %s) !!" % cls.local_ha_state)

        if with_ha:
            cls.remote_client = cls.createClient(cust_host="5.0.0.2")
            # Check HA states locally and remotly

            cls.remote_ha_state = cls.remote_client.call("ha", "getState")[0]
            if cls.remote_ha_state != "CONNECTED":
                test.skip("!! Are you mad ? You're trying to do a HA test without being actually connected (remote state is %s) !!" % cls.remote_ha_state)

            cls.ssh_client = cls.createSSHClient(host="5.0.0.2")

    def test_RAS(self):
        """
            Go to a given working state and check the configuration has 
            correctly been applied.
        """
        # RAZ and quick check we get where we want
        ip0 = u'172.16.0.10'
        self.set_ntp_conf(ip0)
        self.apply_nuconf()
        self.applied_ip = ip0
        self.saved_ip = ip0
        self.correctly_written(NTP, (self.applied_ip,))

    def test_simple(self):
        """
            Simple save and apply test.
        """
        self.to_save_ip = u'172.16.0.23'
        self._test_save()
        self._test_apply()

    def test_reset(self):
        """
            Save twice with two different values then reset.
        """
        self.to_save_ip = u'172.16.0.21'
        self._test_save()
        self.to_save_ip = u'172.16.0.22'
        self._test_save()
        self._test_reset()

    def test_restart(self):
        """
            Save, restart nucentral, apply and restart nucentral.
        """
        self.to_save_ip = u'172.16.0.24'
        self._test_save()
        self._test_restart()
        self._test_apply()
        self._test_restart()

    def set_ntp_conf(self, ip):
        # Let's apply the new configuration
        self.takeNuconfWriteRole()
        self.client.call(   'ntp',
                            'setNtpConfig',
                            {
                                'ntpservers': ip,
                                'isFrozen': False
                            },
                            u'Applying NTP config')

    def nucentral_last_applied_sequence_number(self):
        return self.client.call("config", "getConfigSequenceNumber")
    def remote_nucentral_last_applied_sequence_number(self):
        return self.remote_client.call("config", "getConfigSequenceNumber")

    def nucentral_last_saved_sequence_number(self):
        return self.client.call("config", "getConfigDiffSequenceNumber")

    def remote_nucentral_last_saved_sequence_number(self):
        return self.remote_client.call("config", "getConfigDiffSequenceNumber")

    def logs_last_applied_sequence_number(self):
        command = "grep 'applied configuration sequence number' /var/log/nucentral.log  | tail -n 1 | awk '{ print $NF }'"
        handle = Popen(command, shell=True, stdout=PIPE)
        seq_num = handle.stdout.read().split('\n')[0]
        assert seq_num != '', "!! No 'applied configuration sequence number' in /var/log/nucentral.log !!"
        return int(seq_num)

    def remote_logs_last_applied_sequence_number(self):
        command = "grep 'applied configuration sequence number' /var/log/nucentral.log  | tail -n 1 | awk '{ print $NF }'"
        res = self.sshOutput(command)
        seq_num = res.split('\n')[0]
        assert seq_num != '', "!! No 'applied configuration sequence number' in remote /var/log/nucentral.log !!"
        return int(seq_num)

    def logs_last_saved_sequence_number(self):
        command = "grep 'saved configuration sequence number' /var/log/nucentral.log  | tail -n 1 | awk '{ print $NF }'"
        handle = Popen(command, shell=True, stdout=PIPE)
        seq_num = handle.stdout.read().split('\n')[0]
        assert seq_num != '', "!! No 'saved configuration sequence number' in /var/log/nucentral.log !!"
        return int(seq_num)

    def remote_logs_last_saved_sequence_number(self):
        command = "grep 'saved configuration sequence number' /var/log/nucentral.log  | tail -n 1 | awk '{ print $NF }'"
        res = self.sshOutput(command)
        seq_num = res.split('\n')[0]
        assert seq_num != '', "!! No 'saved configuration sequence number' in remote /var/log/nucentral.log !!"
        return int(seq_num)

    SEQ = re.compile(r"<sequence>([0-9]+)</sequence>")
    def xml_parser_sequence(self, filename):
        with open(filename, 'r') as fd:
            for line in fd:
                match = self.SEQ.search(line)
                if match is not None:
                    return int(match.groups()[0])
        raise Exception('Oops nothing in the xml file matching a sequence number call Feth ASAP!')

    def xml_last_applied_sequence_number(self):
        filename = "/var/lib/nucentral/versionned/configuration/configuration.xml"
        return self.xml_parser_sequence(filename)
    def remote_xml_last_applied_sequence_number(self):
        filename = "/var/lib/nucentral/versionned/configuration/configuration.xml"
        command = "cat %s" % filename
        output = self.sshOutput(command).split('\n')
        for line in output:
            match = self.SEQ.search(line)
            if match is not None:
                return int(match.groups()[0])
        raise Exception('Oops nothing in the remote xml file matching a sequence number call Feth ASAP!')

    def xml_last_saved_sequence_number(self):
        filename = "/var/lib/nucentral/versionned/configuration/saved-configuration.xml"
        return self.xml_parser_sequence(filename)

    def check_exists(self, files, state):
        for filename in files:
            assert exists(filename), "%s is missing %s." % (filename, state)
    def remote_check_exists(self, files, state):
        for filename in files:
            command = "[ -f %s ] && echo exist || echo doesnt_exist" % filename
            result = self.sshOutput(command)
            assert result == "exist\n", "%s doesn't exist on the secondary %s on the primary." % (filename, state)

    def check_doesnt_exist(self, files, state):
        for filename in files:
            assert not exists(filename), "%s is present %s." % (filename, state)
    def remote_check_doesnt_exist(self, files, state):
        for filename in files:
            command = "[ -f %s ] && echo exist || echo doesnt_exist" % filename
            result = self.sshOutput(command)
            assert result == "doesnt_exist\n", "%s exists on the secondary %s on the primary." % (filename, state)

    def check_contains(self, files, to_check):
        for filename in files:
            self.correctly_written(filename, (to_check,))

    def remote_check_contains(self, files, to_check):
        for filename in files:
            self.correctly_written(filename, (to_check,), remote=True)

    def check_doesnt_contain(self, files, to_check):
        for filename in files:
            self.correctly_written(filename, (to_check,), should_find=False)

    def remote_check_doesnt_contain(self, files, to_check):
        for filename in files:
            self.correctly_written(filename, (to_check,), should_find=False, remote=True)

    def check_applied_sequence_coherence(self, state):
        applied = {}
        applied["nucentral"] = self.nucentral_last_applied_sequence_number()
        applied["logs"] = self.logs_last_applied_sequence_number()
        applied["xml"] = self.xml_last_applied_sequence_number()

        errors = []
        if applied["nucentral"] != applied["logs"]:
            error = "nucentral applied sequence number (%d) differs with logs (%d) %s" % \
                    (applied["nucentral"], applied["logs"], state)
            errors.append(error)
        if applied["nucentral"] != applied["xml"]:
            error = "nucentral applied sequence number (%d) differs with xml (%d) %s" % \
                    (applied["nucentral"], applied["xml"], state)
            errors.append(error)

        assert not errors, errors

        # Check remote coherence if asked
        if self.with_ha:
            remote_applied = {}
            remote_applied["nucentral"] = self.remote_nucentral_last_applied_sequence_number()
            remote_applied["logs"] = self.remote_logs_last_applied_sequence_number()
            remote_applied["xml"] = self.remote_xml_last_applied_sequence_number()

            remote_errors = []
            if applied["nucentral"] != applied["logs"]:
                error = "nucentral applied sequence number (%d) differs with logs (%d) %s" % \
                        (applied["nucentral"], applied["logs"], state)
                errors.append(error)
            if applied["nucentral"] != applied["xml"]:
                error = "nucentral applied sequence number (%d) differs with xml (%d) %s" % \
                        (applied["nucentral"], applied["xml"], state)
                errors.append(error)

            assert not remote_errors, errors

    def check_saved_sequence_coherence(self, state, with_xml=False):
        if with_xml and not exists(SAVED):
            assert exists(SAVED), "%s doesn't exist %s" % (SAVED, state)

        saved = {}
        saved["nucentral"] = self.nucentral_last_saved_sequence_number()
        saved["logs"] = self.logs_last_saved_sequence_number()

        errors = []
        if saved["nucentral"] != saved["logs"]:
            error = "nucentral saved sequence number (%d) differs with logs (%d) %s" % \
                    (saved["nucentral"], saved["logs"], state)
            errors.append(error)
        if exists(SAVED):
            saved["xml"] = self.xml_last_saved_sequence_number()
            if saved["nucentral"] != saved["xml"]:
                error = "nucentral saved sequence number (%d) differs with xml (%d) %s" % \
                        (saved["nucentral"], saved["xml"], state)
                errors.append(error)

        assert not errors, errors

# {{{ def _test_save(self):
    def _test_save(self):
        state = "after a save"

        # Store the previous sequence numbers for saved and applied configuration
        last_applied_sequence_number = self.nucentral_last_applied_sequence_number()
        last_saved_sequence_number = self.nucentral_last_saved_sequence_number()

        # Set the IP address as the new ntp configuration
        self.set_ntp_conf(self.to_save_ip)

        # Check we have coherence on the applied sequence numbers
        self.check_applied_sequence_coherence(state)

        # Check we have coherence on the saved sequence numbers
        self.check_saved_sequence_coherence(state, with_xml=True)

        # Were the sequence numbers correctly treated
        new_applied_sequence_number = self.nucentral_last_applied_sequence_number()
        new_saved_sequence_number = self.nucentral_last_saved_sequence_number()

        errors = []
        if not new_saved_sequence_number == (last_saved_sequence_number + 1):
            error = "Saved sequence number wasn't incremented %s (before %d, after %d)" % \
                    (state, new_saved_sequence_number, last_saved_sequence_number)
            errors.append(error)
        if not new_saved_sequence_number != new_applied_sequence_number:
            error = "Saved sequence number is equal to the applied sequence number %s (saved %d, applied %d)" % \
                    (state, new_saved_sequence_number, new_applied_sequence_number)
            errors.append(error)
        if not last_applied_sequence_number == new_applied_sequence_number:
            error = "The applied sequence number has changed %s (before %d, after %d)." % \
                    (state, last_applied_sequence_number, new_applied_sequence_number)
            errors.append(error)
        # End state should be : Applicable
        config_state = self.client.call('config', 'state')
        if not config_state == "Applicable":
            errors.append("config.state is not 'Applicable' error %s (%s)." % (state, config_state))

        assert not errors, errors

        # Check files : modified, existing, non existing
        # Existing :
        should_exist = (SAVED, DIFF, RUNNING, NTP)
        self.check_exists(should_exist, state)
        # Modified :
        should_contain = (SAVED, DIFF)
        self.check_contains(should_contain, self.to_save_ip)
        # UnModified
        shouldnt_contain = (RUNNING, NTP)
        self.check_doesnt_contain(shouldnt_contain, self.to_save_ip)

        # Test parameters
        self.saved_ip = self.to_save_ip
# }}}
# {{{ def _test_reset(self):
    def _test_reset(self):
        state = "after a reset"

        # Store the previous sequence numbers for saved and applied configuration
        last_applied_sequence_number = self.nucentral_last_applied_sequence_number()
        last_saved_sequence_number = self.nucentral_last_saved_sequence_number()

        # Reset the saved configuration
        self.client.call('config', 'reset')

        # Check we have coherence on the applied sequence numbers
        self.check_applied_sequence_coherence(state)

        # Check we have coherence on the saved sequence numbers
        self.check_applied_sequence_coherence(state)

        # Were the sequence numbers correctly treated
        new_applied_sequence_number = self.nucentral_last_applied_sequence_number()
        new_saved_sequence_number = self.nucentral_last_saved_sequence_number()

        errors = []

        if not new_saved_sequence_number <= last_saved_sequence_number:
            error = "Saved sequence number wasn't decremented %s (before %d, after %d)" % \
                        (state, new_saved_sequence_number, last_saved_sequence_number)
            errors.append(error)
        if not new_saved_sequence_number == new_applied_sequence_number:
            error = "Saved sequence number isn't equal to the applied sequence number %s (saved %d, applied %d)" % \
                        (state, new_saved_sequence_number, new_applied_sequence_number)
            errors.append(error)
        if not last_applied_sequence_number == new_applied_sequence_number:
            error = "The applied sequence number has changed %s (before %d, after %d)" % \
                        (state, last_applied_sequence_number, new_applied_sequence_number)
            errors.append(error)
        # End state should be : Idle
        config_state = self.client.call('config', 'state')
        if not config_state == "Idle":
            errors.append("config.state is not 'Idle' %s (%s)" % (state, config_state))

        assert not errors, errors

        # Check files : modified, existing, non existing
        # Existing :
        should_exist = (RUNNING, NTP)
        self.check_exists(should_exist, state)
        # Non Existing
        shouldnt_exist = (SAVED, DIFF)
        self.check_doesnt_exist(shouldnt_exist, state)
        # UnModified
        should_contain = (RUNNING, NTP)
        self.check_contains(should_contain, self.applied_ip)

        # Test parameters
        self.saved_ip = self.applied_ip
# }}}
# {{{ def _test_apply(self):
    def _test_apply(self):
        if self.next_apply_restore:
            state = "after an apply following a restoration"
        else:
            state = "after an apply"
        if self.with_ha:
            state += " (in HA setup)"

        # Store the previous sequence numbers for saved and applied configuration
        last_applied_sequence_number = self.nucentral_last_applied_sequence_number()
        last_saved_sequence_number = self.nucentral_last_saved_sequence_number()
        if self.with_ha:
            remote_last_applied_sequence_number = self.remote_nucentral_last_applied_sequence_number()

        ######################################### Apply the saved configuration
        if self.next_apply_restore:
            self.apply_nuconf(force=True)
        else:
            self.apply_nuconf()
        #######################################################################

        # Check we have coherence on the sequence numbers
        if self.client.call('config', 'state') == "Applicable" \
        and not self.next_apply_restore:
            self.check_saved_sequence_coherence(state, with_xml=True)
        self.check_applied_sequence_coherence(state)

        # Check we have coherence on the saved sequence numbers
        self.check_applied_sequence_coherence(state)

        # Were the sequence numbers correctly treated
        new_applied_sequence_number = self.nucentral_last_applied_sequence_number()
        new_saved_sequence_number = self.nucentral_last_saved_sequence_number()
        if self.with_ha:
            remote_new_applied_sequence_number = self.remote_nucentral_last_applied_sequence_number()

        errors = []

        if not new_saved_sequence_number == new_applied_sequence_number:
            error = "Saved sequence number isn't equal to the applied sequence number %s (saved %d, applied %d)" % \
                     (state, new_saved_sequence_number, new_applied_sequence_number)
            errors.append(error)

        if self.next_apply_restore:
            if not new_applied_sequence_number != last_applied_sequence_number:
                error = "The applied sequence number hasn't changed %s (before %d, after %d)" % \
                        (state, new_applied_sequence_number, last_applied_sequence_number)
                errors.append(error)
        else:
            if not new_applied_sequence_number >= last_applied_sequence_number:
                error = "The applied sequence number hasn't changed after %s" % \
                        (state, new_applied_sequence_number, last_applied_sequence_number)
                errors.append(error)
        # End state should be : Idle
        config_state = self.client.call('config', 'state')
        if not config_state == "Idle":
            errors.append("config.state is not 'Idle' %s (%s)" % (state, config_state))

        assert not errors, errors

        if self.with_ha:
            remote_errors = []
            if not new_applied_sequence_number == remote_new_applied_sequence_number:
                error = "Remote applied sequence number is different to local %s (remote %s, local %s)" % \
                        (state, new_applied_sequence_number, remote_new_applied_sequence_number)
                remote_errors.append(error)
            if not remote_last_applied_sequence_number != remote_new_applied_sequence_number:
                error = "Remote applied sequence number hasn't changed %s (before %s, after %s)" % \
                        (state, remote_last_applied_sequence_number, remote_new_applied_sequence_number)
                remote_errors.append(error)
            assert not remote_errors, remote_errors

        # Check files : modified, existing, non existing
        # Existing :
        should_exist = (RUNNING, NTP)
        self.check_exists(should_exist, state)
        # Non Existing
        shouldnt_exist = (SAVED, DIFF)
        self.check_doesnt_exist(shouldnt_exist, state)
        # Modified
        should_contain = (RUNNING, NTP)
        self.check_contains(should_contain, self.saved_ip)

        if self.with_ha:
            self.remote_check_exists(should_exist, state)
            self.remote_check_doesnt_exist(shouldnt_exist, state)
            self.remote_check_contains(should_contain, self.saved_ip)

        # Test parameters
        self.applied_ip = self.saved_ip
        self.next_apply_restore = False
# }}}
# {{{ def _test_rollback(self):
    def _test_rollback(self):
        if self.next_apply_restore:
            state = "after an apply following a restoration"
        else:
            state = "after an apply"
        if self.with_ha:
            state += " (in HA setup)"

        # Store the previous sequence numbers for saved and applied configuration
        last_applied_sequence_number = self.nucentral_last_applied_sequence_number()
        last_saved_sequence_number = self.nucentral_last_saved_sequence_number()
        if self.with_ha:
            remote_last_applied_sequence_number = self.remote_nucentral_last_applied_sequence_number()

        ######################################### Apply the saved configuration
        if self.next_apply_restore:
            self.apply_nuconf(force=True)
        else:
            self.apply_nuconf()
        #######################################################################

        # Check we have coherence on the sequence numbers
        if self.client.call('config', 'state') == "Applicable" \
        and not self.next_apply_restore:
            self.check_saved_sequence_coherence(state, with_xml=True)
        self.check_applied_sequence_coherence(state)

        # Check we have coherence on the saved sequence numbers
        self.check_applied_sequence_coherence(state)

        # Were the sequence numbers correctly treated
        new_applied_sequence_number = self.nucentral_last_applied_sequence_number()
        new_saved_sequence_number = self.nucentral_last_saved_sequence_number()
        if self.with_ha:
            remote_new_applied_sequence_number = self.remote_nucentral_last_applied_sequence_number()

        errors = []

        if not new_saved_sequence_number == new_applied_sequence_number:
            error = "Saved sequence number isn't equal to the applied sequence number %s (saved %d, applied %d)" % \
                     (state, new_saved_sequence_number, new_applied_sequence_number)
            errors.append(error)

        if self.next_apply_restore:
            if not new_applied_sequence_number != last_applied_sequence_number:
                error = "The applied sequence number hasn't changed %s (before %d, after %d)" % \
                        (state, new_applied_sequence_number, last_applied_sequence_number)
                errors.append(error)
        else:
            if not new_applied_sequence_number >= last_applied_sequence_number:
                error = "The applied sequence number hasn't changed after %s" % \
                        (state, new_applied_sequence_number, last_applied_sequence_number)
                errors.append(error)
        # End state should be : Idle
        config_state = self.client.call('config', 'state')
        if not config_state == "Idle":
            errors.append("config.state is not 'Idle' %s (%s)" % (state, config_state))

        assert not errors, errors

        if self.with_ha:
            remote_errors = []
            if not new_applied_sequence_number == remote_new_applied_sequence_number:
                error = "Remote applied sequence number is different to local %s (remote %s, local %s)" % \
                        (state, new_applied_sequence_number, remote_new_applied_sequence_number)
                remote_errors.append(error)
            if not remote_last_applied_sequence_number != remote_new_applied_sequence_number:
                error = "Remote applied sequence number hasn't changed %s (before %s, after %s)" % \
                        (state, remote_last_applied_sequence_number, remote_new_applied_sequence_number)
                remote_errors.append(error)
            assert not remote_errors, remote_errors

        # Check files : modified, existing, non existing
        # Existing :
        should_exist = (RUNNING, NTP)
        self.check_exists(should_exist, state)
        # Non Existing
        shouldnt_exist = (SAVED, DIFF)
        self.check_doesnt_exist(shouldnt_exist, state)
        # Modified
        should_contain = (RUNNING, NTP)
        self.check_contains(should_contain, self.saved_ip)

        if self.with_ha:
            self.remote_check_exists(should_exist, state)
            self.remote_check_doesnt_exist(shouldnt_exist, state)
            self.remote_check_contains(should_contain, self.saved_ip)

        # Test parameters
        self.applied_ip = self.saved_ip
        self.next_apply_restore = False
# }}}
# {{{ def _test_restart(self):
    def _test_restart(self):
        """
            Test the behaviour of config when we restart nucentral.
        """
        state = "after a nucentral restart"
        previous_state = self.client.call('config', 'state')

        # Store the previous sequence numbers for saved and applied configuration
        last_applied_sequence_number = self.nucentral_last_applied_sequence_number()
        last_saved_sequence_number = self.nucentral_last_saved_sequence_number()

        ##################################################### Restart nucentral
        pid = self.nucentral_pid()
        self.restart_nucentral()
        error = "Nucentral didn't restart."
        assert self.check_nucentral(pid=pid, timeout=50), error
        #######################################################################

        # Check we have coherence on the applied sequence numbers
        self.check_applied_sequence_coherence(state)
        if self.client.call('config', 'state') == "Applicable" \
        and not self.next_apply_restore:
            self.check_saved_sequence_coherence(state, with_xml=True)

        # Check we have coherence on the saved sequence numbers
        self.check_applied_sequence_coherence(state)

        # Were the sequence numbers correctly treated
        new_applied_sequence_number = self.nucentral_last_applied_sequence_number()
        new_saved_sequence_number = self.nucentral_last_saved_sequence_number()
        new_state = self.client.call('config', 'state')

        errors = []

        if not new_saved_sequence_number == last_saved_sequence_number:
            error = "Saved sequence has changed %s (before %d, after %d)." % \
                    (state, new_saved_sequence_number, last_saved_sequence_number)
            errors.append(error)
        if not new_applied_sequence_number == last_applied_sequence_number:
            error = "Applied sequence has changed %s (before %d, after %d)." % \
                    (state, new_applied_sequence_number, last_applied_sequence_number)
            errors.append(error)
        if not previous_state == new_state:
            error = "config.state has changed after %s (before %s, after %s)." % \
                     (state, previous_state, new_state)
            errors.append(error)
        with open("/var/lib/nucentral/versionned/configuration/paths_file") as handle:
            print handle.read
        assert not errors, errors
# }}}
# {{{ def _test_restore(self, force=False):
    def _test_restore(self, force=False):
        if self.local_ha_state == "CONNECTED" and not force:
            raise Exception("Watchout ! You're restoring while on a HA setup. It will deconfigure the primary.")

        state = "after a restoration"
        self.next_apply_restore = True

        try:
            with open('./test_archive/archive.tar.gz', 'rb') as handle:
                content = handle.read()
        except:
            raise Exception("'./test_archive/archive.tar.gz' wasn't found")

        # For this archive, the NTP configuration is 172.16.0.11
        self.to_save_ip = u'172.16.0.11'

        last_applied_sequence_number = self.nucentral_last_applied_sequence_number()

        ############################################################# Restore !
        self.client.call('nurestore', 'restore', encodeFileContent(content))
        #######################################################################

        new_saved_sequence_number = self.nucentral_last_saved_sequence_number()
        new_applied_sequence_number = self.nucentral_last_applied_sequence_number()

        # For this archive, the sequence number is 117
        errors = []

        if not new_saved_sequence_number == 117:
            errors.append("The new saved sequence is not 117 as it should be %s." % state)
        if not last_applied_sequence_number == new_applied_sequence_number:
            errors.append("The applied sequence number has changed %s." % state)
        # End state should be : Applicable
        config_state = self.client.call('config', 'state')
        if not config_state  == "Applicable":
            error = "config.state is not 'Applicable' %s (%s)." % (state, config_state)
            errors.append(error)

        assert not errors, errors

        # Check files : modified, existing, non existing
        # Existing :
        should_exist = (RUNNING, NTP)
        self.check_exists(should_exist, state)
        # Non Existing
        shouldnt_exist = (SAVED, DIFF)
        self.check_doesnt_exist(shouldnt_exist, state)
        # Modified
        should_contain = (RUNNING,)
        self.check_contains(should_contain, self.to_save_ip)
        # UnModified
        shouldnt_contain = (NTP,)
        self.check_doesnt_contain(shouldnt_contain, self.to_save_ip)

        # Test parameters
        self.saved_ip = self.to_save_ip
# }}}
# {{{ def teardown_class(cls):
    @classmethod
    def teardown_class(cls):
        """
            This method is called once when all tests have been done.
            It restores the saved configuration.
        """
        if cls.with_ha:
            cls.ssh_client.close()
        Test.teardown_class()
# }}}
