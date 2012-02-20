"""
Copyright (C) 2007-2011 EdenWall Technologies
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

from socket import socket, AF_INET, SOCK_DGRAM, timeout as socket_timeout, error as socket_error
from logging import INFO
from threading import Event
from time import time

from PyQt4.QtCore import QThread, QObject, SIGNAL, QMutex

from ufwi_rpcd.common.error import reraise, exceptionAsUnicode
from ufwi_rpcd.common.logger import Logger
from ufwi_rpcd.common.streaming import (UDPacket, parseVersion,
    HELLO, VERSION, CONNECT_TIMEOUT, ACK)
from ufwi_rpcd.common import tr
from ufwi_rpcd.client import RpcdError

# Maximum delay in seconds to send the the ack
SEND_TIMEOUT = 5.0

# Maximum inactivity time (in seconds) of a streaming
MAX_IDLE = 60.0

# Check if a stream is down each N seconds
CHECK_PERIOD = 10.0

class StreamingError(RpcdError):
    def __init__(self, message, traceback=None):
        RpcdError.__init__(self, "StreamingError", message, traceback)

class UDPStreamingThread(QThread, Logger):
    def __init__(self, logger, sock):
        Logger.__init__(self, "streaming")
        QThread.__init__(self)
        self._run_mutex = QMutex()
        self._stop_mutex = QMutex()
        self._run_event = Event()
        self.next_check = time() + CHECK_PERIOD
        self.sock = sock

    def waitRun(self, timeout=30):
        self._run_event.wait(timeout)

    def getPort(self):
        self.waitRun(None)
        return self.port

    def run(self):
        try:
            self._run()
        except Exception, err:
            self.writeError(err, "run() error")

    def _run(self):
        self._run_mutex.lock()
        try:
            self._run_event.set()
            self.waitPackets()
        finally:
            self._run_mutex.unlock()
            self.sock.close()

    def waitPackets(self):
        while self._stop_mutex.tryLock():
            self._stop_mutex.unlock()
            if self.readPacket():
                break

            # Every n seconds, ask main thread to check if we correctly receive
            # each streams, in the case the server is down, or something like this.
            if time() < self.next_check:
                self.next_check = time() + CHECK_PERIOD
                self.emit(SIGNAL('checkStreams()'))

    def readPacket(self):
        """
        Read packet from socket.

        @return  True if we want to close socket
        """
        self.sock.settimeout(0.250)
        try:
            data = self.sock.recv(512)
        except socket_timeout:
            return False
        except socket_error, err:
            self.writeError(err, "recvfrom() error #%s" % err[0])
            return False

        if not data:
            self.debug("Client has exited!")
            return True

        self.sock.settimeout(SEND_TIMEOUT)
        try:
            self.sock.send(ACK)
        except socket_error, err:
            self.writeError(err, "send() error #%s" % err[0])
            # send() is a fatal error. It may occur with an iptable OUTPUT rule
            # (DROP or REJECT)
            return True

        packet = UDPacket()
        packet.unSerialize(data)
        self.emit(SIGNAL('messageReceived(PyQt_PyObject)'), packet)
        return False

    def stopRun(self):
        self._stop_mutex.lock()
        self._run_mutex.lock()
        self._run_mutex.unlock()
        self._stop_mutex.unlock()
        self.wait()

class Handler:

    def __init__(self, id, callback, period, component, service, args):

        self.id = id
        self.callback = callback
        self.period = period
        self.component = component
        self.service = service
        self.args = args
        self.timeout = time() + max(MAX_IDLE, self.period * 3)

    def call(self, packet):
        self.timeout = time() + max(MAX_IDLE, self.period * 3)
        self.callback(packet)

class UDPStreamingReceiver(QObject, Logger):

    def __init__(self, client):

        QObject.__init__(self)
        Logger.__init__(self, "streaming")
        self.client = client
        self.handlers = {}   # stream identifier (int) => Handler

        sock = self.createSocket()
        self.port = sock.getsockname()[1]
        self.thread = UDPStreamingThread(self, sock)
        self.thread.start()
        self.thread.waitRun()

        self.connect(self.thread, SIGNAL('messageReceived(PyQt_PyObject)'), self.messageReceived)
        self.connect(self.thread, SIGNAL('checkStreams()'), self.checkStreams)

    def createSocket(self):
        host = self.client.host
        port = self.client.streaming_port
        self.info("Connecting to %s:%s (udp)..." % (host, port))
        before = time()
        sock = socket(AF_INET,SOCK_DGRAM)
        try:
            sock.settimeout(CONNECT_TIMEOUT)
            sock.connect((host, port))
            sock.send(HELLO)
            server_hello = sock.recv(50)
            if server_hello != HELLO:
                sock.close()
                server_version = parseVersion(server_hello)
                raise StreamingError(
                    tr("Server streaming version (%s) is different from the client version (%s)!")
                    % (server_version, VERSION))
        except socket_error, err:
            sock.close()
            self.writeError(err, "Unable to connect to %s:%s" % (host, port))
            reraise(StreamingError(
                tr("Unable to connect streaming to %s:%s: %s")
                % (host, port, exceptionAsUnicode(err))))
        after = time()
        diff = "%1.f ms" % ((after - before) * 1000.0)
        self.warning("Connected to %s:%s (%s)" % (host, port, diff))
        return sock

    def subscribe(self, callback, period, component, service, args):

        id = self.client.call('streaming', 'subscribe', self.port, period, component, service, args)
        self.debug('Subscribed to %d' % id)
        self.handlers[id] = Handler(id, callback, period, component, service, args)

        return id

    def unsubscribe(self, id):

        try:
            self.handlers.pop(id)
            self.debug('Unsubscribed from %d' % id)

            self.client.call('streaming', 'unsubscribe', id)
        except (KeyError, ValueError):
            # Not subscribed
            pass
        except RpcdError, err:
            self.writeError(err, 'Unable to unsubscribe a stream', log_level=INFO)

    def checkStreams(self):
        # Get outdated streams
        now = time()
        reconnect = [handler
            for id, handler in self.handlers.iteritems()
            if handler.timeout < now]

        # Reconnect streams
        for handler in reconnect:
            self.unsubscribe(handler.id)
            try:
                self.debug('It seems that the stream %d is down: resubscribe' % id)
                self.subscribe(handler.callback, handler.period, handler.component, handler.service, handler.args)
            except RpcdError, err:
                self.writeError(err, 'Unable to subscribe to a stream', log_level=INFO)

    def messageReceived(self, packet):

        try:
            if packet.id in self.handlers:
                handler = self.handlers[packet.id]
            else:
                self.client.call('streaming', 'unsubscribe', packet.id)
                return
        except KeyError:
            # Not subscribed
            self.warning('Warning: received an invalid stream (%s)' % packet.id)
            self.client.call('streaming', 'unsubscribe', packet.id)
            return
        handler.call(packet)

    def stop(self):
        self.thread.stopRun()

