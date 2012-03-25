# TODO test with deferred in callback

from nucentral.core.notify import Notify

def cb_event1(context, test):
    test['cb_event1'] = 'done'

def cb_event2(context, test):
    test ['coin'] = context.test_arg

class TestNotify:
    def setup_class(cls):
        cls.test = {}
        cls.notify = Notify()
        cls.obj1 = cls.notify.connect('config', 'event1', cb_event1, cls.test)
        cls.obj2 = cls.notify.connect('*', 'event2', cb_event2, cls.test)

    def test_specific1(self):
        self.notify.emit('config', 'event1')
        del self.test['cb_event1']

    def test_specific2(self):
        ret = self.notify.emit('test_sender', 'event2', test_arg='test')
        assert self.test['coin'] == 'test'
        del self.test['coin']

    def test_specific3(self):
        assert self.notify.disconnect('config', 'event1', self.obj1)
        self.obj1 = None
        self.notify.emit('config', 'event1')
        assert len(self.test) == 0

    def test_specific4(self):
        assert self.notify.disconnect('*', 'event2', self.obj2)
        self.obj2 = None
        self.notify.emit('config', 'event2', test_arg='void')
        self.notify.emit('test_sender', 'event2', test_arg='coin')
        assert len(self.test) == 0

    def test_isConnected(self):
        """test isConnected method"""
        def useless():
            pass

        assert not self.notify.isConnected('test_test_test', 'test_test_test', useless)
        connected1 = self.notify.connect('*', '_event3_', useless)
        assert self.notify.isConnected('*', '_event3_', useless)
        assert self.notify.disconnect('*', '_event3_', connected1)

        connected1 = self.notify.connect('config', '_event4_', useless)
        assert self.notify.isConnected('config', '_event4_', useless)
        assert self.notify.disconnect('config', '_event4_', connected1)
