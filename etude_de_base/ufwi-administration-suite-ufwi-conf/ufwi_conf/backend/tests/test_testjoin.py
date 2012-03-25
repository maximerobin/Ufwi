from ufwi_conf.backend.net_ads import net_ads_testjoin

from common import NoopLogger, execs, preseed, CommandTestBase

_NET_ADS_STDERR_BASIC = """\
[2010/05/27 20:47:28,  0] param/loadparm.c:7473(lp_do_parameter)
  Ignoring unknown parameter "idmap domains"
"""

_NET_ADS_STDERR_NO_LOGON = """\
[2010/05/27 12:14:39,  0] utils/net_ads.c:279(ads_startup_int)
  ads_connect: No logon servers
Join to domain is not valid: No logon servers
"""

class TestTestJoinCmd(CommandTestBase):

    def checkcmd(self):
        previous_execs_len = len(execs)
        result = net_ads_testjoin(
            NoopLogger
            )
        assert len(execs) == previous_execs_len + 1
        assert execs[-1:] == [
            (
                ['net', 'ads', 'testjoin'],
                None
            )
        ]
        return result

    def test_testjoin_ok(self):
        preseed("Join is OK", '', 0)
        result = self.checkcmd()
        assert result

    def test_testjoin_ok_with_stderr_garbage(self):
        preseed(
            "Join is OK",
            _NET_ADS_STDERR_BASIC,
            0
        )
        result = self.checkcmd()
        assert result

    def test_testjoin_nok_nomessage(self):
        preseed("", '', 255)
        result = self.checkcmd()
        assert not result

    def test_testjoin_nok_message(self):
        preseed(
            "",
            _NET_ADS_STDERR_NO_LOGON,
            255
        )
        result = self.checkcmd()
        assert not result

if __name__ == '__main__':
    testobject = TestTestJoinCmd()
    for testmethod in (
        testobject.test_testjoin_ok,
        testobject.test_testjoin_ok_with_stderr_garbage,
        testobject.test_testjoin_nok_nomessage,
        testobject.test_testjoin_nok_message,
        ):
        testobject.setup_method(testmethod)
        testmethod()
        testobject.teardown_method(testmethod)


