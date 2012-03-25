
"""
Copyright (C) 2009-2011 EdenWall Technologies

This file is part of NuFirewall. 
 
 NuFirewall is free software: you can redistribute it and/or modify 
 it under the terms of the GNU General Public License as published by 
 the Free Software Foundation, version 3 of the License. 
 
 NuFirewall is distributed in the hope that it will be useful, 
 but WITHOUT ANY WARRANTY; without even the implied warranty of 
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the 
 GNU General Public License for more details. 
 
 You should have received a copy of the GNU General Public License 
 along with NuFirewall.  If not, see <http://www.gnu.org/licenses/>
"""

import time, datetime
from twisted.python.failure import Failure
from ufwi_rpcd.backend.cron import RpcdTask
from ufwi_rpcd.backend.cron import scheduleOnce
from ufwi_rpcd.backend import tr
from ufwi_rpcd.backend.error import RpcdError, exceptionAsUnicode

SCHEDULED, RUNNING, FINNISHED = range(3)

class MultiSiteTask:
    #States:
    def __init__(self, core, ctx, fw, sched_options):
        self.core = core
        self.ctx = ctx
        self.fw = fw
        self.delayed_task = None
        self.task = None
        self.task_stop_on_success = True
        self.task_retry_time = 0
        self.sched_options = None
        self.status = ''
        self.state = SCHEDULED
        self.id = -1

        self.reschedule(sched_options)

    def setID(self, id):
        self.id = id

    def cancelTask(self):
        # Stop a previous task if it's running
        if self.delayed_task:
            self.delayed_task.cancel()
            self.delayed_task = None
        if self.task and self.task.isStarted():
            self.taskDone("done")

            # force stopping
            if not self.task_stop_on_success:
                self.task.stop()

            # Wait for the task to be effectivly stopped
            while self.task.isStarted():
                time.sleep(0.5)

            # force stopping
            if not self.task_stop_on_success:
                self.stop_callback()

        self.sched_options = None
        self.status = ''

    def reschedule(self, sched_options):
        self.task_retry_time = sched_options['retry_time']
        self.sched_options = sched_options
        if self.task_retry_time < 5:
            self.task_retry_time = 5
        self.task_stop_on_success = sched_options['stop_on_success']

        start_date = sched_options['start_date']
        if start_date != 0:
            start_date = start_date - time.time()
            now = datetime.datetime.now()
            now += datetime.timedelta(seconds = start_date)
            self.status = tr(u'Starting on %s') % now.strftime("%x %X")
        else:
            self.sched_options['start_date'] = time.time()

        if start_date <= 0:
            self.firstStart()
        else:
            self.delayed_task = scheduleOnce(start_date, self.firstStart)

    def firstStart(self):
        self.state = RUNNING
        self.delayed_task = None
        self.task = RpcdTask(self.task_retry_time, self.taskMain)
        self.task.start()
        self.taskMain()

    def taskMain(self):
        d = self.checkConnection()
        d.addCallback(self.checkState)
        d.addCallback(lambda x:self.callback())
        d.addCallback(self.taskDone)
        d.addErrback(self.taskDone)

    def checkConnection(self):
        return self.core.callService(self.ctx, 'multisite_master', 'getFirewallState', self.fw.name)

    def checkState(self, status):
        if status != self.fw.ONLINE:
            now = datetime.datetime.now()
            now += datetime.timedelta(seconds = self.task_retry_time)
            self.status = tr(u'Firewall not available. Retrying on %s') % now.strftime("%x %X")
            raise Exception(self.status)
        return True

    def taskDone(self, ret):
        if isinstance(ret, Failure):
            self.setError(ret.getErrorMessage())
            self.fw.error(tr("Error while performing task on firewall %s: %s") % (self.fw.name, str(ret.getErrorMessage())))
            self.fw.debug(tr("Error while applying updates to firewall %s: %s") % (self.fw.name, str(ret.getTraceback())))
            return

        if self.task_stop_on_success:
            self.state = FINNISHED
            self.task.stop()

    def getSchedule(self):
        if self.sched_options is None:
            return None
        sched = self.sched_options
        sched['status'] = self.status
        sched['description'] = self.getDescription()
        sched['id'] = self.id
        return sched

    def setError(self, err):
        self.status = exceptionAsUnicode(err)

    def callback(self):
        raise NotImplemented

    def stop_callback(self):
        raise NotImplemented

    def getDescription(self):
        raise NotImplemented

    @classmethod
    def getRWRole(cls, rw):
        if not rw in ['read', 'write', 'admin']:
            raise RpcdError(tr('Unhandled role type'))
        return cls.getRole() + rw

    @classmethod
    def getRole(cls):
            raise NotImplemented

