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

from PyQt4.QtCore import QThread, QObject, SIGNAL, QMutex
from ufwi_rpcd.common.logger import Logger
from ufwi_rpcd.client.error import RpcdError
from threading import Event
from time import time
import cPickle as pickle
from copy import copy

class Deferred(object):

    def __init__(self, *args, **kwargs):
        self.args = args
        self.result = None
        self.error = False
        self.callbacks = []
        self.errbacks = []
        self.callbackArgsList = []
        self.callbackKeywordsList = []
        self.errbackArgsList = []
        self.errbackKeywordsList = []
        self.cache = 0
        self.last = 0

        if 'callback' in kwargs:
            self.callbacks.append(kwargs.get('callback'))
        if 'errback' in kwargs:
            self.errbacks.append(kwargs.get('errback'))

        self.callbackArgs = kwargs.get('callbackArgs', ())
        assert isinstance(self.callbackArgs, tuple)
        self.errbackArgs = kwargs.get('errbackArgs', ())
        assert isinstance(self.errbackArgs, tuple)
        self.callbackKeywords = kwargs.get('callbackKeywords', {})
        assert isinstance(self.callbackKeywords, dict)
        self.errbackKeywords = kwargs.get('errbackKeywords', {})
        assert isinstance(self.errbackKeywords, dict)

        self._addArgs(self)

        if 'cache' in kwargs:
            self.cache =  kwargs.get('cache')
            # not: bool derives from int
            if not isinstance(self.cache, (int,long)) or isinstance(self.cache, bool):
                self.cache = 2

    def addCallbacks(self, d):
        self.callbacks.extend(d.callbacks)
        self.errbacks.extend(d.errbacks)
        self._addArgs(d)

    def _addArgs(self, d):
        self.callbackArgsList.append(d.callbackArgs)
        self.callbackKeywordsList.append(d.callbackKeywords)
        self.errbackArgsList.append(d.errbackArgs)
        self.errbackKeywordsList.append(d.errbackKeywords)

    def update(self, d):
        self.error = d.error
        self.result = d.result

    def __str__(self):
        return pickle.dumps(self.args)

    def __eq__(self, d):
        return str(self) == str(d)

class AsyncClientThread(QThread, Logger):

    def __init__(self, client):
        Logger.__init__(self, "async_client")
        QThread.__init__(self)
        self._run_mutex = QMutex()
        self._stop_mutex = QMutex()
        self._queue_mutex = QMutex()
        self._queue_event = Event()
        self._run_event = Event()

        self.client = client
        self.queue = set()
        self.cache = {}

    def waitRun(self, timeout=30):
        self._run_event.wait(timeout)

    def run(self):
        try:
            self._run()
        except Exception, err:
            self.writeError(err, "run() error")

    def _run(self):
        self._run_mutex.lock()
        self._run_event.set()
        try:
            while self._stop_mutex.tryLock():
                self._stop_mutex.unlock()

                # Wait for new events
                self._queue_event.wait(0.250)
                if not self._queue_event.isSet():
                    continue

                # Read events
                self._queue_mutex.lock()
                try:
                    self._queue_event.clear()
                    while len(self.queue):
                        deferred = self.queue.pop()

                        self._queue_mutex.unlock()
                        self.call(deferred)
                        self._queue_mutex.lock()
                finally:
                    self._queue_mutex.unlock()

        finally:
            self._run_mutex.unlock()

    def stopRun(self):
        self._stop_mutex.lock()
        self._run_mutex.lock()
        self._run_mutex.unlock()
        self._stop_mutex.unlock()
        self.client.logout()
        self.wait()

    def enqueue(self, deferred):
        try:
            self._queue_mutex.lock()

            to_rem = []
            now = time()
            cached = None
            for id, c in self.cache.iteritems():
                if (now - c.last) > c.cache and c.result:
                    to_rem.append(id)
                elif id == str(deferred):
                    cached = c
            for id in to_rem:
                self.cache.pop(id)

            # Information is cached
            if cached and cached.result:
                deferred.update(cached)
            else:
                if deferred.cache and not cached:
                    self.cache[str(deferred)] = copy(deferred)
                self.queue.add(deferred)
                self._queue_event.set()
                return
        finally:
            self._queue_mutex.unlock()

        self.emit(SIGNAL('gotResponse(PyQt_PyObject)'), deferred)

    def dequeue(self, callback):
        try:
            self._queue_mutex.lock()

            for id, d in self.cache.iteritems():
                try:
                    d.callbacks.remove(callback)
                except ValueError:
                    continue

                if not d.callbacks:
                    try:
                        # FIXME: while 1? WTF?
                        while 1:
                            self.queue.remove(d)
                    except KeyError:
                        pass

            to_rem = set()
            for queued in self.queue:
                if callback in queued.callbacks:
                    to_rem.add(queued)

            for queued in to_rem:
                self.queue.remove(queued)
        finally:
            self._queue_mutex.unlock()

    def flushQueue(self):
        try:
            self._queue_mutex.lock()
            self.queue.clear()
        finally:
            self._queue_mutex.unlock()

    def call(self, deferred):

        try:
            if not deferred.callbacks:
                return

            deferred.result = self.client.call(*deferred.args)
            deferred.error = False
        except Exception, err:
            deferred.result = err
            deferred.error = True

        try:
            self._queue_mutex.lock()
            if deferred.cache:
                try:
                    cached = self.cache[str(deferred)]
                    cached.update(deferred)
                    cached.last = time()
                    deferred = copy(cached)

                    try:
                        while 1:
                            self.queue.remove(cached)
                    except KeyError:
                        pass
                except KeyError:
                    # Not cached
                    pass
        finally:
            self._queue_mutex.unlock()

        self.emit(SIGNAL('gotResponse(PyQt_PyObject)'), deferred)

class AsyncClient(QObject):
    """
        how to use with one callback and/or errback :
            async = self.client.async()
            async.call(component, service, arg1, arg2, ...,
                callback = self.successDiag,
                errback = self.errorDiag,
                callbackArgs=(filename,),
                )

        how to use with two or more callbacks :
            def1 = Deferred(component, service, arg1, arg2, ...,
                            callback = self.success, errback = self.error,
                            callbackArgs=(...),
                            callbackKeywords={...}
                            errbackArgs=(...),
                            errbackKeywords={...})
            def2 = Deferred(callback = self.success2, errback = self.error2, callbackArgs=('plop1',), errbackArgs=('plop2',))
            def1.addCallbacks(def2)
            async = self.client.async()
            async.thread.enqueue(def1)

            def success(self, ret_of_service_call, *args, **kwargs):
            def error(self, Exception, *args, **kwargs):
            def success2(self, ret_of_service_call, *args, **kwargs):
            def error2(self, Exception, *args, **kwargs):

            API differs from twisted deferred:
                - values returned by component.services() are passed to all callbacks
                  (in twisted only the first callback will receive returned values)
                - you can not pass arguments from callback to next callback
                  ( for example from success to success2)
    """
    def __init__(self, client, client_base=None):

        QObject.__init__(self)

        self.client_base = client_base
        self.thread = AsyncClientThread(client)
        self.connect(self.thread, SIGNAL('gotResponse(PyQt_PyObject)'), self.gotResponse)
        self.thread.start()
        self.thread.waitRun()

    def call(self, *args, **kwargs):
        """
            Call asynchonously a service.
            @param args [tuple] all unnamed arguments will be sent to
                                ufwi_rpcd.
            @param callback [callable] called after received result from
                                       ufwi_rpcd.
            @param errback [callable] when service raises an error, this
                                      function is called.
            @param cache [bool] do use cache
        """

        try:
            self.client_base.record_call(args)
        except Exception:
            pass
        self.thread.enqueue(Deferred(*args, **kwargs))

    def unref(self, callback):
        """ Uncrement reference on this call """
        self.thread.dequeue(callback)

    def flushQueue(self):
        self.thread.flushQueue()

    def gotResponse(self, deferred):
        # don't keep references to useless or used args/kwargs
        if deferred.error:
            methods = deferred.errbacks
            argsList = deferred.errbackArgsList
            kwargsList = deferred.errbackKeywordsList
            if 0 == deferred.cache:
                del deferred.callbackArgsList[:]
                del deferred.callbackKeywordsList[:]
        else:
            methods = deferred.callbacks
            argsList = deferred.callbackArgsList
            kwargsList = deferred.callbackKeywordsList
            if 0 == deferred.cache:
                del deferred.errbackArgsList[:]
                del deferred.errbackKeywordsList[:]

        for index, func in enumerate(methods):
            if 0 == deferred.cache:
                args = argsList.pop(0)
                kwargs = kwargsList.pop(0)
            else:
                args = argsList[index]
                kwargs = kwargsList[index]
            func(deferred.result, *args, **kwargs)

    def stop(self):
        self.thread.stopRun()
