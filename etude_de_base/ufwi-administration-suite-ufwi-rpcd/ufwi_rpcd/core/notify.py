"""
Copyright (C) 2010-2011 EdenWall Technologies
Written by Victor Stinner <vstinner AT edenwall.com>

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
from itertools import chain
from twisted.internet.defer import inlineCallbacks
from ufwi_rpcd.common.human import humanRepr
from ufwi_rpcd.backend.logger import Logger

class Callback:
    def __init__(self, func, args, kw):
        self.func = func
        self.args = args
        self.kw = kw

    def __call__(self, context):
        self.func(context, *self.args, **self.kw)

    def __str__(self):
        return humanRepr(self.func)

class CallbackContext:
    def __init__(self, sender, event, extra):
        for attr, value in extra.iteritems():
            setattr(self, attr, value)
        self.sender = sender
        self.event = event

class Notify(Logger):
    """
    Connect events to callbacks.

    An event is an arbitrary string, eg. "ufwi_rulesetApply".
    """
    def __init__(self):
        Logger.__init__(self, "notify")

        # (event: str, sender: str) => list of Callback objects
        self.events = {}
        # event: str => list of Callback objects
        self.generic_events = {}

        # ConfigComponent (will be set later)
        self.config = None

    @inlineCallbacks
    def emit(self, sender, event, **extra):
        """
        Emit an event: call callbacks connected to this event.
        Return a deferred object.

        Extra arguments can be set using keywords, they will be available as
        context attributes:

            notify.emit('nupki', 'updateCRL', pki_name='test')
            => context.pki_name == 'test'
        """
        message = "%s emitted signal %s" % (sender, event)
        if extra:
            message += " (%s)" % humanRepr(extra)
        self.warning(message)
        specific_cb = self.events.get((sender, event), [])
        generic_cb = self.generic_events.get(event, [])
        callbacks = chain(specific_cb, generic_cb)
        context = CallbackContext(sender, event, extra)
        for callback in callbacks:
            self.debug("Event %s.%s: call %s" % (sender, event, callback))
            try:
                yield callback(context)
            except Exception, err:
                self.writeError(err, "Error on callback %s" % callback)

    def connect(self, sender, event, func, *args, **kw):
        """
        Connect an event sent by sender to a callback. emit() will call:

           func(context, *args, **kw)

        where context is a CallbackContext.

        If sender parameter is '*', func will be called whatever value of
        'sender' is passed by 'emit'.

        Return the callback object. Use it to disconnect() the callback.
        """
        callback = Callback(func, args, kw)
        key, events = self.selectKeyAndEvents(sender, event)

        if key in self.events:
            events[key].append(callback)
        else:
            events[key] = [callback]

        return callback

    def disconnect(self, sender, event, callback):
        """
        Disconnect the callback from the event of the sender.

        Return True on success, False if the callback was no registered.
        """
        key, events = self.selectKeyAndEvents(sender, event)

        try:
            events[key].remove(callback)
            return True
        except (KeyError, ValueError):
            return False

    def isConnected(self, sender, event, func):
        """return True if already connected with same sender and event"""
        key, events = self.selectKeyAndEvents(sender, event)
        if key in events:
            for callback in events[key]:
                if callback.func == func:
                    return True

        return False

    def selectKeyAndEvents(self, sender, event):
        if sender != '*':
            return (sender, event), self.events
        else:
            return event, self.generic_events

