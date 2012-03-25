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

from time import time
from datetime import timedelta
from twisted.application.internet import UDPServer
from twisted.internet.protocol import DatagramProtocol

from ufwi_rpcd.common.streaming import UDPacket, HELLO, ACK
from ufwi_rpcd.common.human import humanRepr, fuzzyTimedelta

from ufwi_rpcd.backend import tr, RpcdError, Component, SessionError
from ufwi_rpcd.backend.cron import scheduleRepeat
from ufwi_rpcd.backend.error import exceptionAsUnicode
from ufwi_rpcd.backend.logger import Logger, ContextLoggerChild

from ufwi_rpcd.core import events

# Tolerate no answer during MIN_IDLE seconds
MIN_IDLE = 30

class StreamingError(RpcdError):
    pass

class Stream(ContextLoggerChild):
    def __init__(self, streaming, context, host, port, period, component, service, args):
        ContextLoggerChild.__init__(self, context, streaming)

        if period < 1:
            raise StreamingError(
                tr("Stream period (%s) is shorter than 1 second"),
                period)
        # Ensure that context is allowed to access the requested service
        streaming.core.getService(context, component, service)

        self.core = streaming.core
        self.host = host
        self.context = context
        self.port = port
        self.period = period
        self.component = component
        self.service = service
        self.transport = streaming.transport
        self.last_ack = time()
        self.max_idle = max(MIN_IDLE, period * 3)

        self.args = (self.component, self.service)
        self.kw = {}
        if isinstance(args, dict):
            self.kw = args
        elif isinstance(args, (tuple, list)):
            self.args += tuple(args)
        else:
            self.args += (args,)

        # Attributes set by UDPStreaming.addStream()
        self.id = None
        self.cron = None

    def ack(self):
        self.last_ack = time()

    def __eq__(self, stream):
        return self.id == stream.id

    def callService(self):
        return self.core.callService(self.context, *self.args, **self.kw)

    def sendData(self, result):
        if isinstance(result, UDPacket):
            packet = result
            packet.id = self.id
        else:
            packet = UDPacket(self.id, result)
        bytes = packet.serialize()
        self.transport.write(bytes, (self.host, self.port))

    def sendError(self, err):
        self.writeError(err, "Error on sending data to %s" % self)
        try:
            text = exceptionAsUnicode(err)
            packet = UDPacket(error=text)
            self.sendData(packet)
        except Exception, err:
            self.writeError(err, "Error on sending error to %s" % self)
        self.stop()

    def run(self):
        diff = time() - self.last_ack
        if self.max_idle < diff:
            diff = timedelta(seconds=diff)
            self.error("Stop %s: no answer since %s"
                % (self, fuzzyTimedelta(diff)))
            self.stop()
            return
        try:
            result = self.callService()
            result.addCallback(self.sendData)
            result.addErrback(self.sendError)
            return result
        except Exception, err:
            self.writeError(err, 'Error in %s' % self)
            self.stop()

    def __str__(self):
        return 'stream #%s (%s:%s)' % (self.id, self.host, self.port)

    def stop(self):
        if not self.cron:
            return
        if self.cron.running:
            self.cron.stop()
        self.cron = None

class UDPStreaming(DatagramProtocol, Logger):
    def __init__(self, core):
        Logger.__init__(self, "UDPStreaming")
        self.core = core
        self.streams = {}  # identifier (int) => Stream
        self.address_to_streams = {}  # IP host => set of Stream identifiers
        self.next_id = 1   # generate unique stream identifiers
        events.connect('sessionDestroyed', self.sessionDestroyed)

    def ack(self, host, port):
        try:
            identifiers = self.address_to_streams[(host, port)]
        except KeyError:
            return
        for identifier in identifiers:
            stream = self.streams[identifier]
            stream.ack()

    def datagramReceived(self, data, host_port):
        (host, port) = host_port
        if data == ACK:
            self.ack(host, port)
        else:
            hello = humanRepr(data, 50)
            self.critical("Connection from %s:%s: hello=%s" % (host, port, hello))
            self.transport.write(HELLO, (host, port))

    def __del__(self):
        events.disconnect('sessionDestroyed', self.sessionDestroyed)

    def sessionDestroyed(self, session):
        streams = self.streams.values()
        for stream in streams:
            try:
                stream_session = stream.context.getSession()
                if stream_session != session:
                    continue
            except SessionError:
                # session is expired, removing it too.
                pass
            self._removeStream(stream)

    def addStream(self, context, stream):
        stream.id = self.next_id
        self.next_id += 1
        context.stream_id = stream.id
        self.streams[stream.id] = stream
        key = (stream.host, stream.port)
        try:
            self.address_to_streams[key].add(stream.id)
        except KeyError:
            self.address_to_streams[key] = set((stream.id,))
        stream.cron = scheduleRepeat(stream.period, stream.run)
        return stream.id

    def _removeStream(self, stream):
        identifier = stream.id
        del self.streams[identifier]
        key = (stream.host, stream.port)
        self.address_to_streams[key].remove(identifier)
        stream.stop()

    def removeStream(self, context, id):
        try:
            stream = self.streams[id]
        except KeyError:
            return False

        if stream.context.getSession() != context.getSession():
            raise StreamingError(tr('You are not allowed to delete this streaming'))

        self._removeStream(stream)
        return True

    def removeAllStreams(self):
        for stream in self.streams.itervalues():
            stream.stop()
        self.streams.clear()
        self.address_to_streams.clear()

class StreamingComponent(Component):

    NAME = "streaming"
    VERSION = "1.0"
    API_VERSION = 2

    def init(self, core):
        port = core.config.getint('CORE', 'streaming_udp_port')
        self.core = core

        core.warning("Starting the UDP streaming service")
        self.streaming = UDPStreaming(core)
        server = UDPServer(port, self.streaming)
        core.setupService(server)

    def checkServiceCall(self, context, service_name):
        # streaming is only allowed to authenticated users
        if not context.isAuthenticatedUser():
            service = "%s.%s()" % (self.name, service_name)
            raise StreamingError(
                tr("Only authenticated users can use the %s service"),
                service)

    def service_subscribe(self, context, port, period, component, service, args):
        stream = Stream(self.streaming, context, context.user.host, port, period, component, service, args)
        return self.streaming.addStream(context, stream)

    def service_unsubscribe(self, context, id):
        return self.streaming.removeStream(context, id)

    def destroy(self):
        self.streaming.removeAllStreams()

