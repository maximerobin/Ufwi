from ufwi_conf.backend.net_ads import net_ads_keytab_command

from common import NoopLogger, execs, CommandTestBase

class TestKeytabCmd(CommandTestBase):

    def test_keytab_create(self):
        previous_execs_len = len(execs)
        net_ads_keytab_command(
            NoopLogger,
            'username',
            'password',
            'create'
            )
        assert len(execs) == previous_execs_len + 1
        assert execs[-1:] == [
            (
                ['net', 'ads', '-U', 'username%password', 'keytab', 'create'],
                'net ads -U ***user***  ***pass*** keytab create'
            )
        ]

    def test_keytab_add_nuauth(self):
        previous_execs_len = len(execs)
        net_ads_keytab_command(
            NoopLogger,
            'username',
            'password',
            'add nuauth'
            )
        assert len(execs) == previous_execs_len + 1
        expected = [
            (
                ['net', 'ads', '-U', 'username%password', 'keytab', 'add', 'nuauth'],
                'net ads -U ***user***  ***pass*** keytab add nuauth'
            )
        ]
        assert execs[-1:] == expected, 'expected:\n%s\n but got:\n%s' % (expected, execs[:1])

if __name__ == '__main__':
    testobject = TestKeytabCmd()
    for testmethod in (
        testobject.test_keytab_create,
        testobject.test_keytab_add_nuauth
        ):
        testobject.setup_method(testmethod)
        testmethod()
        testobject.teardown_method(testmethod)


