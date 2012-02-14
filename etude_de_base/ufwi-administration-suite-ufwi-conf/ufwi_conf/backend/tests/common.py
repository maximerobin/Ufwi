from StringIO import StringIO
from collections import deque

from ufwi_rpcd.backend import process

execs = []
preseeds = deque()

def backupfunc(function, incl_name=True):
    """
    backups whatever is useful in function
    """
    backup = {
        'func_code': function.func_code,
        'func_defaults': function.func_defaults,
        'func_globals': function.func_globals.copy(),
    }

    if incl_name:
        backup['func_name'] = function.func_name

    return backup

def restorefunc(function, backup):
    """
    takes a backup as generated by backupfunc and transforms function
    """
    function.func_code = backup['func_code']
    function.func_defaults = backup['func_defaults']
    if 'func_name' in backup:
        function.func_name = backup['func_name']

    #func_globals is a read only attribute
    function.func_globals.clear()
    function.func_globals.update(backup['func_globals'])

class FakeProcess(object):
    def __init__(self):
        if len(preseeds) == 0:
            stdout = stderr = ''
            status = 0
        else:
            stdout, stderr, status = preseeds.pop()

        self.stdout = StringIO(stdout)
        self.stderr = StringIO(stderr)
        self.status = status

def _runCommand(
        logger,
        command,
        **kwargs
    ):
        command_log = kwargs.get('cmdstr')
        execs.append(
            (command, command_log)
        )

def runCommandOk(*args, **kwargs):
    _runCommand(*args, **kwargs)
    fakeprocess = FakeProcess()
    return fakeprocess, fakeprocess.status

_runcommand_backup = None

def setup_fake_runCommand():
    global _runcommand_backup, _runcommand_shell
    if _runcommand_backup is None:
        #only backup once
        _runcommand_backup = backupfunc(process.runCommand)
    replacement = runCommandOk
    fake_backup = backupfunc(replacement, incl_name=False)
    func = process.runCommand
    restorefunc(func, fake_backup)
    process.runCommand = func

def teardown_fake_runCommand():
    global _runcommand_backup
    restorefunc(process.runCommand, _runcommand_backup)
    _runcommand_backup = None

class NoopLogger(object):
    @staticmethod
    def debug(message):
        print 'debug:', message
    @staticmethod
    def info(message):
        print 'info:', message
    @staticmethod
    def warning(message):
        print 'info:', message
    @staticmethod
    def error(message):
        print 'error:', message
    @staticmethod
    def critical(message):
        print 'critical:', message

class CommandTestBase(object):

    def setup_method(self, meth):
        setup_fake_runCommand()

    def teardown_method(self, meth):
        teardown_fake_runCommand()

def preseed(stdout, stderr, status):
    preseeds.appendleft(
        (stdout, stderr, status)
        )

