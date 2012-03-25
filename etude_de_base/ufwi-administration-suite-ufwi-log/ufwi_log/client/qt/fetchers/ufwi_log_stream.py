# -*- coding: utf-8 -*-

"""
Copyright (C) 2008-2011 EdenWall Technologies
Written by Romain Bignon <romain AT inl.fr>

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

from copy import deepcopy, copy
from PyQt4.QtCore import SIGNAL, QTimer
from ufwi_rpcd.common import tr
from ufwi_rpcc_qt.streaming import StreamingError
from ufwi_log.client.qt.fetchers.base import BaseFetcher

class NulogStreamFetcher(BaseFetcher):

    table_size = 20
    default_interval = 1

    def isPrintable(self): return False

    def __init__(self, fragment, args, client):
        BaseFetcher.__init__(self, fragment, args, client)

        self.available_args = None
        self.stream_id = 0
        self.table = []
        self.columns = []
        self.paused_table = None
        self.firewall = ''
        self.error = None
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.connect(self.timer, SIGNAL('timeout()'), self.sendUpdate)
        self.type = 'streaming'


    def unsubscribe(self):
        if not self.stream_id:
            return
        streaming = self.client.streaming()
        streaming.unsubscribe(self.stream_id)
        self.stream_id = 0

    def destructor(self):
        if self.stream_id:
            self.timer.stop()
            self.unsubscribe()

    def subscribe(self):
        if self.stream_id > 0:
            self.unsubscribe()

        if not self.fragment.args.has_key('interval'):
            self.fragment.args['interval'] = self.default_interval

        self.my_args = deepcopy(self.fragment.args)
        self.my_args.update(self.args)
        self.columns = [] # will reset data
        self.table = []
        self.firewall = self.fragment.firewall

        if self.NULOG_VERSION == '3.0':
            service = 'table'
        else:
            service = 'stream'

        streaming = self.client.streaming()
        if not streaming:
            raise StreamingError(tr("(streaming is disabled)"))

        if self.fragment.firewall:
            self.stream_id = streaming.subscribe(self.recvPacket, self.my_args['interval'],
                                                             'multisite_master', 'callRemote', (self.fragment.firewall,
                                                             'ufwi_log', service, self.fragment.type, self.my_args))
        else:
            self.stream_id = streaming.subscribe(self.recvPacket, self.my_args['interval'],
                                                             'ufwi_log', service, (self.fragment.type, self.my_args))

    def pause(self, b):
        if b:
            self.paused_table = copy(self.table)
        else:
            self.paused_table = None

    def sendUpdate(self):
        self.emit(SIGNAL('want_update'))

    def recvPacket(self, packet):
        try:
            self.addEntry(packet)

            # To prevent a wide draw-loop in case there is a lag or
            # something like this, which can freeze the interface,
            # we do not draw less than the 'interval/2' interval.
            if not self.timer.isActive():
                self.timer.start(500 * self.fragment.args['interval'])

            args = deepcopy(self.fragment.args)
            args.update(self.args)
            if args != self.my_args or self.firewall != self.fragment.firewall:
                self.subscribe()
        except Exception, err:
            self.unsubscribe()
            self.error = err
            self.sendUpdate()

    def addEntry(self, packet):
        if packet and packet.data and len(packet.data[0]) == 0:
            return

        if packet.error:
            raise Exception(packet.error)

        if not self.columns or self.columns != packet.columns:
            self.columns = packet.columns
            self.table = []
            for i in xrange(self.table_size, 0, -1):
                line = [packet.timestamp - i*self.fragment.args['interval']]
                line += [0 for j in xrange(len(packet.data))]
                self.table.append(line)

        self.table = self.table[1:]
        try:
            self.table.append([packet.timestamp] + [int(i) for i in packet.data])
        except ValueError:
            raise Exception('Received malformated data')

    def getArgs(self):
        if self.available_args is None:
            self.available_args = self.call('ufwi_log', 'table_filters', self.fragment.type)
        return self.available_args

    def count(self, callback):
        return callback(len(self.table))

    def fetch(self, callback):
        try:
            self._fetch(callback)
        except Exception, err:
            self._errorHandler(err)


    def getTime(self, callback):
        pass

    def _fetch(self, callback):
        if self.error:
            self._errorHandler(self.error)
            self.error = None
            return

        if self.stream_id == 0:
            self.subscribe()

        # Arguments have changed
        args = deepcopy(self.fragment.args)
        args.update(self.args)
        if args != self.my_args or self.firewall != self.fragment.firewall:
            self.subscribe()

        if self.paused_table is None:
            table = self.table
        else:
            table = self.paused_table

        callback({'args': self.my_args,
                  'filters': self.my_args,
                  'columns': self.columns,
                  'rowcount': len(table),
                  'table': table,
                 })

class RealTimeStreamFetcher(NulogStreamFetcher):
    def addEntry(self, packet):
        self.table = packet.data

