"""
a lock file manager: a config application will be resumed across reboots

Copyright (C) 2009-2011 EdenWall Technologies
Written by Feth AREZKI <farezki AT edenwall.com>

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
from __future__ import with_statement

from os.path import exists
from os import unlink
from logging import error
from threading import Lock
import errno

from ufwi_rpcd.common.logger import LoggerChild
from ufwi_rpcd.core.lock import LockError

def lock(method):
    def new_method(self):
        if self.threading_lock.locked():
            raise LockError("Race condition? Lock already owned")
        self.threading_lock.acquire()
        result = method(self)
        self.threading_lock.release()
        return result
    return new_method

class ApplyLock(LoggerChild):
    def __init__(self, logger, lock_file):
        LoggerChild.__init__(self, logger)

        self.threading_lock = Lock()
        self.lock_file = lock_file

    @lock
    def exists(self):
        return exists(self.lock_file)

    @lock
    def create(self):
        with open(self.lock_file, 'w') as fd:
            fd.write("Nucentral Apply in progress\n")

    @lock
    def delete(self):
        try:
            unlink(self.lock_file)
        except OSError, err:
            if err.errno == errno.ENOENT:
                error("[config] apply_lock unexpectedly missing as I try to delete it")
            else:
                raise

