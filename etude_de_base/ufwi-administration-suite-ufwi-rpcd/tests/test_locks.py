
"""
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

from nucentral.core.lock import LockingComponent, LockError
from nucentral.core.mockup import Core

def test_volatile():
    lc = fake_volatile_init()

    def log_callback(a_lock):
        print "callback called for lock", a_lock

    #Acquire, release

    lock = lc.acquireVolatile("key_a", log_callback)
    lc.releaseVolatile("key_a", lock)

    #Acquire, reacquire, same key: must fail
    lock = lc.acquireVolatile("key_a", log_callback)
    try:
        lc.acquireVolatile("key_a", log_callback)
    except LockError:
        pass
    else:
        assert False, "The lock should be reserved already!"

    #Acquire, release, not owner: must fail
    lc.acquireVolatile("key_c", log_callback)
    try:
        lc.releaseVolatile("key_c", lock)
    except LockError:
        pass
    else:
        assert False, "The key is wrong!"

    #FIXME: NOT TESTED:
    #-keepVolatileAlive
    #-purgeVolatiles

def fake_volatile_init():
    core = Core()
    locking_component = LockingComponent()
    locking_component.init(core)
    return locking_component

if __name__ == "__main__":
    test_volatile()

