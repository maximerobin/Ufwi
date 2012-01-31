"""
Copyright (C) 2007-2011 EdenWall Technologies
Written by Pierre Chifflier <p.chifflier AT inl.fr>

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

$Id$
"""

from twisted.internet import reactor
from twisted.internet import task
from twisted.internet.defer import Deferred

DAILY_CHECK_INTERVAL_SECONDS = 300

def scheduleOnce(delay, callback, *args, **kwargs):
    """ Schedule execution of callback once.
    Callback is executed after waited "delay" seconds

    """
    return reactor.callLater(delay, callback, *args, **kwargs)

def scheduleRepeat(period, callback, *args, **kwargs):
    """ Schedule execution of callback periodically.
    Callback is executed immediately, then every "period" seconds
    """
    t = task.LoopingCall(callback, *args, **kwargs)
    t.start(period)
    return t

def scheduleDaily(hour, minute, callback, *args, **kwargs):
    """ Schedule execution of callback daily, at about the given time.
    callback may be executed twice (if scheduleDaily is called at a multiple
    of DAILY_CHECK_INTERVAL_SECONDS since the given time) or more (if
    ufwi-rpcd is restarted between the given time and
    DAILY_CHECK_INTERVAL_SECONDS later).
    """
    import time
    def run_if_on_time(cb):
        localtime = time.localtime()
        targettime = localtime[:3] + (hour, minute, 0) + localtime[6:]
        diff = time.mktime(localtime) - time.mktime(targettime)
        if diff >= 0 and diff <= DAILY_CHECK_INTERVAL_SECONDS:
            cb(*args, **kwargs)
    scheduleRepeat(DAILY_CHECK_INTERVAL_SECONDS, run_if_on_time, callback,
                   *args, **kwargs)

class RpcdTask():
    def __init__(self, period, callback, *args, **kwargs):
        self.is_started = False
        self.want_stop = False
        self.period = period
        self.args = args
        self.kwargs = kwargs
        self.cb = callback

    def start(self, err = True):
        self.is_started = True
        scheduleOnce(self.period, self.triggerTask)

    def stop(self):
        self.want_stop = True
        self.is_started = False

    def isStarted(self):
        return self.is_started

    def triggerTask(self):
        if self.want_stop:
            self.is_started = False
            return
        r = self.cb(*self.args, **self.kwargs)
        if isinstance(r, Deferred):
            r.addCallback(self.start)
            r.addErrback(self.start)
        else:
            self.start()
