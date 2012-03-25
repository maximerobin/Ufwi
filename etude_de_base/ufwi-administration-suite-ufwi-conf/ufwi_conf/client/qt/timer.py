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


from PyQt4.QtCore import QEvent, QObject, QTimer, SIGNAL

from time import time

class Timer(QTimer):
    """
    a wrapper for qtimer
    """
    def __init__(self, callback, interval, keepalive, parent):
        QTimer.__init__(self)
        self.server_up = True
        self.is_visible = False
        self.setInterval(interval)

        self.start_time = None
        self.remaining_time = None

        QObject.connect(self, SIGNAL('timeout()'), callback)
        QObject.connect(keepalive, SIGNAL("keepAliveQuery"), self.pause)
        QObject.connect(keepalive, SIGNAL("serverUp"), self.serverUp)
        QObject.connect(keepalive, SIGNAL("serverDown"), self.serverDown)

        parent.installEventFilter(self)

    def pause(self):
        """
        stop timer, store remaining duration
        """
        if not self.isActive():
            return False

        self.remaining_time = (time() - self.start_time) * 1000
        self.stop()
        return True

    def resume(self):
        """
        resume timer with remaining duration
        """
        if self.isActive() or self.remaining_time is None:
            return False

        self.start(self.remaining_time)
        return True

    def isPaused(self):
        """
        return True if timer is waiting
        """
        return self.remaining_time is not None

    def serverUp(self):
        """
        if connection become up, resume the timer
        """
        if not self.server_up:
            self.server_up = True

        if self.is_visible:
            if self.isPaused():
                self.start(self, self.remaining_time)
            else:
                self.start()
        else:
            self.remaining_time = None

    def serverDown(self, unused):
        """
        if connection is lost, stop the timer
        """
        if self.server_up:
            self.server_up = False
            self.stop()
        self.remaining_time = None

    def eventFilter(self, unused, event):
        """
        transmit all events, start/stop timer when parent is shown/hidden
        """
        if event.type() == QEvent.Show:
            self.is_visible = True
            if not self.isActive() and self.server_up:
                self.start()
        elif event.type() == QEvent.Hide:
            self.is_visible = False
            if self.isActive():
                self.stop()
            elif self.isPaused():
                self.remaining_time = None
        return False

    def start(self, interval=None):
        self.start_time = time()
        self.remaining_time = None
        if interval is None:
            QTimer.start(self)
        else:
            QTimer.start(self, interval)
