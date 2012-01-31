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

from twisted.internet.defer import _parseDListResult, DeferredList, \
    succeed, maybeDeferred

def gatherResults(deferredList):
    """
        Our version of twisted gatherResults() to consume errors
        raised in deferreds callbacks, as by default, they will
        not be handled (but errback will call anyway).
    """


    # Twisted has a parameter to DeferredList to do what we want to
    d = DeferredList(deferredList, fireOnOneErrback=1, consumeErrors=1)
    d.addCallback(_parseDListResult)

    return d

class Callback:
    def __init__(self, func, *args, **kw):
        self.func = func
        self.args = args
        self.kw = kw

    def __call__(self, value):
        return self.func(value, *self.args, **self.kw)

class TryFinally:
    def __init__(self, func, *args, **kw):
        self.prepare_cb = None
        self.try_cb = Callback(func, *args, **kw)
        self.finally_cb = None
        self.error_cb = None

    def setPrepare(self, func, *args, **kw):
        self.prepare_cb = Callback(func, *args, **kw)

    def setFinally(self, func, *args, **kw):
        self.finally_cb = Callback(func, *args, **kw)

    def setError(self, func, *args, **kw):
        self.error_cb = Callback(func, *args, **kw)

    def _returnError(self, value, err):
        return err

    def _finallyError(self, err):
        defer = maybeDeferred(self.finally_cb, err)
        defer.addCallback(self._returnError, err)
        return defer

    def _tryBlock(self, value):
        defer = maybeDeferred(self.try_cb, value)
        if self.finally_cb:
            defer.addErrback(self._finallyError)
        return defer

    def execute(self, value):
        defer = succeed(value)
        if self.prepare_cb:
            defer.addCallback(self.prepare_cb)
        defer.addCallback(self._tryBlock)
        if self.finally_cb:
            defer.addCallback(self.finally_cb)
        if self.error_cb:
            defer.addErrback(self.error_cb)
        return defer

