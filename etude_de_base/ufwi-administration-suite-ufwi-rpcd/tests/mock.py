
from nucentral.core.mockup import NullLogger

class Config(object):
    def __init__(self, vardir):
        self.vardir = vardir

    def get(self, section, key):
        if (section, key) == ('CORE', 'vardir'):
            return self.vardir
        else:
            raise ValueError("Unknown section or key")

class Notify(object):
    def emit(*args, **kwargs):
        pass

class Core(object):
    def __init__(self, vardir):
        self.config = Config(vardir)
        self.notify = Notify()

class FakeComponent(NullLogger):
    def __init__(self, core):
        self.core =  core
        self.name = "fake component"

