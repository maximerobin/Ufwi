from ufwi_rpcd.core.mockup import Core
from ufwi_conf.backend import unix_service

if __name__ == '__main__':
    from common import CommandTestBase, execs
else:
    from .common import CommandTestBase, execs

def noop(*args, **kwargs):
    pass

class TestUnixService(CommandTestBase):
    def test_init(self):
        class EmptyUnixService(unix_service.UnixServiceComponent):
            VERSION = '1'
            CONFIG_DEPENDS = ()
            read_config = noop
            apply_config = noop

        component = EmptyUnixService()
        component.init(Core())

        return component

    def test_setEnabled(self):
        component = self.test_init()
        execs_size_before = len(execs)
        component.service_setEnabledOnBoot(
            None,
            True
        )
        execs_nb = len(execs)
        expected_execs_nb = execs_size_before + 2
        assert execs_nb == expected_execs_nb, "Supposed to run 2 commands. Before: %d ran, after: %s" % (execs_size_before, execs_nb)
        assert execs[-2:] == [
            (['/usr/sbin/update-rc.d', '-f', '/bin/false', 'remove'], None),
            (['/usr/sbin/update-rc.d', '-f', '/bin/false', 'defaults', '20', '20'], None)
        ]

    def test_disable(self):
        component = self.test_init()
        execs_size_before = len(execs)
        component.service_setEnabledOnBoot(
            None,
            False
        )
        assert len(execs) == execs_size_before + 1, "Supposed to run 1 command"
        assert execs[-1:] == [
            (['/usr/sbin/update-rc.d', '-f', '/bin/false', 'remove'], None),
        ]

if __name__ == '__main__':
    testobject = TestUnixService()
    for testmethod in (
        testobject.test_init,
        testobject.test_setEnabled,
        testobject.test_disable,
        ):
        testobject.setup_method(testmethod)
        testmethod()
        testobject.teardown_method(testmethod)

