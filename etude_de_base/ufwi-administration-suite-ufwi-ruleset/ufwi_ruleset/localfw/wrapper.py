from twisted.internet.defer import inlineCallbacks

class LocalFW:
    def __init__(self, filename):
        self.filename = filename
        self.calls = []

    def call(self, *args):
        self.calls.append(args)

    @inlineCallbacks
    def execute(self, core, context):
        def localfw(*args):
            return core.callService(context, 'localfw', *args)

        yield localfw('open', self.filename)
        try:
            yield localfw('clear')
            for args in self.calls:
                yield localfw(*args)
            yield localfw('apply')
        finally:
            yield localfw('close')

