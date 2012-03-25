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

from ufwi_rpcd.common.error import RPCD_ERRORS, writeError

class EventManager:
    event_map = dict()


def connect(name,callback):
    """ Connect callback function to event.
    If the same callback is already connected to the same event,
    nothing is done.
    """
    evm = EventManager
    if not evm.event_map.has_key(name):
        evm.event_map[name] = []
    if not (callback in evm.event_map[name]):
        evm.event_map[name].append(callback)

def disconnect(name,callback):
    """ Remove the callback function associated with event
    """
    evm = EventManager
    if evm.event_map.has_key(name):
        if callback in evm.event_map[name]:
            evm.event_map[name].remove(callback)
        if len(evm.event_map[name]) == 0:
            del evm.event_map[name]

def disconnectAll(name,callback):
    """ Remove all callback functions associated with event
    """
    evm = EventManager
    if evm.event_map.has_key(name):
        del evm.event_map[name]

def emit(name,*args, **kwargs):
    """ Send event and call all associated functions, passing arguments
    """
    evm = EventManager
    if name not in evm.event_map:
        return
    for callback in evm.event_map[name]:
        try:
            callback(*args, **kwargs);
        except RPCD_ERRORS, err:
            writeError(err, "Error on calling %s for event %r"
                % (callback, name))

