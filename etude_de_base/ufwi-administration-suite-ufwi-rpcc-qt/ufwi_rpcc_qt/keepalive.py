#coding: utf-8
"""
$Id$


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


from threading import Event
from PyQt4.QtCore import QObject, SIGNAL, QThread, QMutex
from time import time, sleep

from ufwi_rpcd.common import tr
from ufwi_rpcd.client import RpcdError, KEEP_ALIVE_SECONDS

class KeepAliveThread(QThread):
    def __init__(self, client, delay=None):
        QThread.__init__(self)
        self.server_up = True
        if delay:
            self.delay = delay
        else:
            self.delay = KEEP_ALIVE_SECONDS
        self._run_mutex = QMutex()
        self._stop_mutex = QMutex()
        self._run_event = Event()
        self.next_keepalive = time()
        self.client = client.clone("keepalive")
        self.logger = self.client

    def waitRun(self, timeout=30):
        self._run_event.wait(timeout)

    def run(self):
        self.next_keepalive = time() + self.delay
        try:
            self._run()
        except Exception, err:
            self.logger.writeError(err, "run() error")

    def _run(self):
        self._run_mutex.lock()
        try:
            self._run_event.set()
            while self._stop_mutex.tryLock():
                self._stop_mutex.unlock()
                self.keepAlive()
            self.client.logout()
        finally:
            self._run_mutex.unlock()

    def keepAlive(self):
        sleep(0.250)
        now = time()
        if now < self.next_keepalive:
            return
        try:
            self.client.call('session', 'keepAlive')
        except RpcdError, err:
            if self.server_up:
                self.server_up = False
                self.emit(SIGNAL("serverDown"), err)
        else:
            if not self.server_up:
                self.server_up = True
                self.emit(SIGNAL("serverUp"))
        self.next_keepalive = time() + self.delay

    def stop(self):
        self._stop_mutex.lock()
        self._run_mutex.lock()
        self._run_mutex.unlock()
        self._stop_mutex.unlock()
        self.wait()

class KeepAlive:
    def __init__(self, window):
        self.window = window
        self.thread = KeepAliveThread(window.client)
        QObject.connect(self.thread, SIGNAL("serverUp"), self.serverUp)
        QObject.connect(self.thread, SIGNAL("serverDown"), self.serverDown)
        self.thread.start()
        self.thread.waitRun()
        self.wait_popup = False

    def stop(self):
        self.thread.stop()

    def serverUp(self):
        self.window.setStatus(tr("Connected"))
        if not self.wait_popup:
            self.wait_popup = True
            try:
                self.window.information(tr("The configuration server is available again."))
            finally:
                self.wait_popup = False

    def serverDown(self, err):
        self.window.setStatus(tr("Disconnected"))
        if not self.wait_popup:
            self.wait_popup = True
            try:
                self.window.ufwi_rpcdError(err,
                    tr("Unable to update the session! Is the configuration server still running?"))
            finally:
                self.wait_popup = False

