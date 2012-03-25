from ufwi_rpcd.core.mockup import Core
from ufwi_conf.backend.tests.common import execs, preseed, CommandTestBase

from .nuauth import NuauthComponent

_SAMPLE_AD_INFO = """\
Realm: Sample realm
Server time offset: 0s
LDAP server name: winbidule.domain.com
We ought to add more info here, real and maybe false
"""

_AD_INFO_VERSION_1 = 1

def run(nuauth_component, success, last_realm):
    execs_len_before = len(execs)

    if success:
        preseed('Join is OK', '', 0)
        preseed(_SAMPLE_AD_INFO, '', 0)
        cmd_nb = 2
    else:
        preseed('Join to domain is not valid: No logon servers', '', 255)
        cmd_nb = 1

    result = nuauth_component.ad_info(_AD_INFO_VERSION_1)
    assert success == result['current status']

    assert result['realm'] == last_realm
    assert len(execs) == execs_len_before + cmd_nb
    assert execs[-cmd_nb] == (
        ['net', 'ads', 'testjoin'],
        None
        )
    if success:
        assert execs[-1] == (
            ['net', 'ads', 'info'],
            None,
            )

class TestNuauthComponent(CommandTestBase):
    def test_ad_info(self):
        nuauth_component = NuauthComponent()
        nuauth_component.init(Core())

        run(nuauth_component, False, '')
        run(nuauth_component, True, 'Sample realm')
        run(nuauth_component, False, 'Sample realm')

