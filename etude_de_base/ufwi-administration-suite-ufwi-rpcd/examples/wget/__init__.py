from __future__ import with_statement
from nucentral.backend import Component
from nucentral.backend.cron import scheduleOnce
from os.path import basename, join as path_join
from urllib import url2pathname
from nucentral.backend.process import createProcess

class DownloadTask:
    def __init__(self, component, url, login):
        filename = url2pathname(url)
        filename = basename(url)
        if not filename:
            raise Exception('Empty filename')

        self.url = url
        self.process = None
        self.owner = login
        self.component = component
        self.filename = path_join(component.download_dir, filename)
        self.log_filename = self.filename + '.log'
        self._process = createProcess(component,
            ['wget', self.url, '-o', self.log_filename, '-O', self.filename],
            locale=False)
        self._schedule()

    def status(self):
        with open(self.log_filename, 'r') as f:
            return f.readlines()

    def _schedule(self):
        scheduleOnce(1.0, self._poll)

    def _poll(self):
        status = self._process.poll()
        if status is None:
            self._schedule()
            return
        self._process = None
        self.component.taskDone(self, status == 0)
        # FIXME: copy useless info from the log file and delete the log file

class Wget(Component):
    NAME = "wget"
    API_VERSION = 2
    VERSION = "1.0"
    ROLES = {
        'ruleset_read': set(('download', 'progress', 'successes', 'failures')),
        'ruleset_write': set(('@ruleset_read', 'download', 'clear')),
    }

    def init(self, core):
        self.tasks = {}
        self.successes = []
        self.failures = []
        self.download_dir = '/tmp'

    def service_download(self, context, url):
        try:
            task = self.tasks[url]
        except KeyError:
            pass
        else:
            raise Exception(
                "%s is already downloading (user %s)"
                % (url, task.owner))
        task = DownloadTask(self, url, context.user.login)
        self.tasks[url] = task
        task.start(self)

    def service_progress(self, context):
        status = {}
        for task in self.tasks.itervalues():
            if task.owner != context.user.login:
                continue
            status[task.url] = task.status()
        return status

    def service_successes(self, context):
        successes = {}
        for task in self.successes:
            successes[task.url] = task.status()
        return successes

    def service_failures(self, context):
        failures = {}
        for task in self.failures:
            failures[task.url] = task.status()
        return failures

    def service_clear(self, context):
        del self.successes[:]
        del self.failures[:]

    def taskDone(self, task, success):
        del self.tasks[task.url]
        if success:
            self.successes.append(task)
        else:
            self.failures.append(task)

    def checkServiceCall(self, context, service_name):
        if (not context.user) or (not context.user.login):
            raise Exception(
                "Service %s() requires an authenticated user" % service_name)

