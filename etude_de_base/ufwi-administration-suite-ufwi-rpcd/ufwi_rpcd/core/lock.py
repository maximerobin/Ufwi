#coding: utf-8
"""
Copyright (C) 2007-2011 EdenWall Technologies
Written by Victor Stinner <victor.stinner AT inl.fr>

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
from ConfigParser import NoOptionError
from os.path import join as path_join, basename
from os import unlink
import weakref
import threading
from glob import glob

from ufwi_rpcd.common import tr
from ufwi_rpcd.common.error import exceptionAsUnicode
from ufwi_rpcd.common.tools import abstractmethod, safeFilenameRegex

from ufwi_rpcd.backend import RpcdError
from ufwi_rpcd.backend.component import Component
from ufwi_rpcd.backend.cron import scheduleRepeat
from ufwi_rpcd.backend.exceptions import ConfigError

# Should be a valid filename
KEY_REGEX = safeFilenameRegex(3)

DEFAULT_VOLATILE_TIMEOUT = 60   # seconds

CLEANUP_PERIOD = 60 # seconds

class LockError(RpcdError):
    pass

class AlreadyAcquired(LockError):
    """
    by_other is True if lock have been acquired by other
    """
    def __init__(self, by_other, *args, **kwargs):
        self.by_other = by_other
        LockError.__init__(self, *args, **kwargs)

class Lock(object):
    @abstractmethod
    def isValid(self):
        pass

    @abstractmethod
    def contextHasLock(self, context):
        pass

class PersistentLock(Lock):
    def __init__(self, key, session, filename):
        self.on_disk = False
        self.key = key
        self.session_ref = weakref.ref(session)
        self.filename = filename

    def write(self):
        session = self.getSession()
        fp = open(self.filename, 'w')
        fp.write(session.cookie)
        fp.close()
        self.on_disk = True

    def getSession(self):
        return self.session_ref()

    def isValid(self):
        return (self.getSession() is not None)

    def destroy(self):
        if not self.on_disk:
            return
        self.on_disk = False
        try:
            unlink(self.filename)
        except IOError, err:
            raise LockError("Could not delete lock file: %s" % exceptionAsUnicode(err))

    def contextHasLock(self, context):
        if context.isUserContext():
            return context.getSession().getID() == self.getSession().cookie
        else:
            return False

class VolatileLock(Lock):
    """
    This lock is not written on disk (not persistent across reboots) and callbacks a function when destroy() is called

    In config, callback_fn is redefined when release is called. This is not orthodox, so I repeat this information here.
    """
    def __init__(self, callback_fn, volatile_timeout):
        self.callback_fn = callback_fn
        self.volatile_timeout = volatile_timeout

        self.expiration = 0

        #sets self.expiration:
        self.keepAlive()

    def isValid(self):
        return self.expiration < time()

    def keepAlive(self):
        now = time()
        self.expiration =  now + self.volatile_timeout

    def destroy(self):
        #NOTE: this signature might change to indicate context.
        self.callback_fn(self)

class ComponentLock(Lock):
    def __init__(self, component):
        Lock.__init__(self)
        self.component = component

    def isValid(self):
        return True

    def getComponentName(self):
        return self.component.name

    def destroy(self):
        return

    def contextHasLock(self, context):
        if context.isComponentContext():
            return context.component.name == self.component.name
        else:
            return False

class LockingComponent(Component):
    """
    Session to acquire or release a lock.
    """

    NAME = "lock"
    VERSION = "1.0"
    API_VERSION = 2
    ROLES = {
        "nucentral_admin": set(("list",)),
    }

    def init(self, core, testing=False):
        # key (str) -> ComponentLock or PersistentLock
        self.permanent_locks = {}
        self.volatile_locks = {}
        self.thread_lock = threading.Lock()
        self.cleanup_task = scheduleRepeat(CLEANUP_PERIOD, self.cleanup)

        self.init_core(core)

    def init_core(self, core):
        vardir = core.config.get('CORE', 'vardir')
        self.directory = path_join(vardir, "locks")

        self.volatile_timeout = self.getConfigLockTimeout(core)

        # Store a reference in core object
        core.lock_manager = self

    def getConfigLockTimeout(self, core):

        #method 3: will always work
        volatile_timeout = DEFAULT_VOLATILE_TIMEOUT

        #method 2: second preferred
        try:
            volatile_timeout = core.config.getfloat('CORE', 'LockTimeout')
        except NoOptionError:
            self.debug('Option "LockTimeout" not set in etc config file')

        #method 1: user defined value
        try:
            volatile_timeout = core.config_manager.get('core', 'lock', 'timeout')
        except (AttributeError, ConfigError):
            self.debug('Option "core / lock / timeout" not set in customized configuration, or config not loaded yet')

        if volatile_timeout is None:
            volatile_timeout = DEFAULT_VOLATILE_TIMEOUT

        return volatile_timeout

    def load(self, session_manager):
        for filename in glob(path_join(self.directory, "*")):
            try:
                self.loadLock(session_manager, filename)
            except Exception, err:
                self.writeError(err, "Unable to restore the lock from the file %r" % basename(filename))
                # Remove the buggy lock file
                try:
                    unlink(filename)
                except OSError, err:
                    self.warning("Error deleting a lock file: %s", err)
        if self.permanent_locks:
            self.error("Reload %s locks" % len(self.permanent_locks))

    def loadLock(self, session_manager, filename):
        lock = session_manager.fromFilename(filename)
        if not lock:
            return
        self.permanent_locks[lock.key] = lock

    def destroy(self):
        self.cleanup_task.stop()

    def cleanup(self):
        self.purgePermanent()
        self.purgeVolatiles()

    def purgePermanent(self):
        remove = []
        for key, lock in self.permanent_locks.iteritems():
            if lock.isValid():
                continue
            remove.append(key)
        for key in remove:
            self.destroyLock(key)

    def purgeVolatiles(self):
        remove = []
        for key, lock in self.volatile_locks.iteritems():
            if lock.isValid():
                return
            remove.append((key, lock))
        for key, lock in remove:
            del self.volatile_locks[key]
            lock.destroy()

    def destroyLock(self, key):
        lock = self.permanent_locks[key]
        #Explicitely let flow LockError from here
        lock.destroy()
        del self.permanent_locks[key]

    def destroyVolatile(self, key):
        #FIXME: obvious factorisation with destroyLock
        lock = self.volatile_locks[key]
        lock.destroy()
        del self.volatile_locks[key]

    def releaseVolatile(self, key, lock):
        self.thread_lock.acquire()
        try:
            self._releaseVolatile(key, lock)
        finally:
            self.thread_lock.release()

    def _releaseVolatile(self, key, lock):
        key = self.cleanKey(key)

        try:
            if self.volatile_locks[key] != lock:
                raise LockError("lock/key do not match")
        except KeyError:
            raise LockError("No such lock")

        del self.volatile_locks[key]
        lock.destroy()

    def acquireVolatile(self, key, callback_fn):
        # callback_fn prototype:
        # def callback(lock): ...
        self.thread_lock.acquire()
        try:
            return self._acquireVolatile(key, callback_fn)
        finally:
            self.thread_lock.release()

    def _acquireVolatile(self, key, callback_fn):
        key = self.cleanKey(key)

        if key not in self.volatile_locks:
            lock = VolatileLock(callback_fn, self.volatile_timeout)
            self.volatile_locks[key] = lock
            return lock
        else:
            raise LockError(tr('The "%s" lock is not available'), key)

    def acquire(self, context, key):
        session = context.getSession()

        self.thread_lock.acquire()
        try:
            key = self.cleanKey(key)

            # Check whether the lock already exists
            if key in self.permanent_locks:
                lock = self.permanent_locks[key]

                if isinstance(lock, PersistentLock):
                    lock_session = lock.getSession()

                    if lock_session:
                        if lock_session == session:
                            raise AlreadyAcquired(False,
                                tr('You already own the "%s" lock'), key)
                        else:
                            raise AlreadyAcquired(True,
                                tr('The "%s" lock is already owned by %s'),
                                key, unicode(lock_session.user))
                    else:
                        # Session lost: destroy the associated lock
                        self.destroyLock(key)
                elif isinstance(lock, ComponentLock):
                    raise LockError(
                        tr('The "%s" lock is already owned by the %s component'),
                        key, unicode(lock.getComponentName()))

            # Create the lock
            filename = path_join(self.directory, key)
            if context.component:
                lock = ComponentLock(context.component)
            else:
                lock = PersistentLock(key, session, filename)
                lock.write()
            self.permanent_locks[key] = lock
        finally:
            self.thread_lock.release()


    def cleanKey(self, key):
        if isinstance(key, str):
            try:
                key = unicode(key, 'ASCII')
                valid = True
            except UnicodeDecodeError:
                valid = False
        else:
            valid = isinstance(key, unicode)
        if valid:
            valid = KEY_REGEX.match(key)
        if not valid:
            raise LockError(tr("Invalid lock key: %s"), repr(key))
        return key

    def release(self, context, key):
        self.thread_lock.acquire()
        try:
            key = self.cleanKey(key)

            # Get the lock
            if key in self.permanent_locks:
                lock = self.permanent_locks[key]
            else:
                raise LockError(tr('The "%s" lock is not acquired!'), key)

            # PersistentLock owned by another user?
            if isinstance(lock, PersistentLock):
                session = context.getSession()
                lock_session = lock.getSession()
                if lock_session != session:
                    raise LockError(
                        tr('The "%s" lock, owned by %s, can not be released!'),
                        key, unicode(lock_session.user))
            elif isinstance(lock, ComponentLock):
                if lock.getComponentName() != context.component.name:
                    raise LockError(
                        tr('The "%s" lock, owned by the %s component, can not be released!'),
                        key, unicode(lock.getComponentName()))
            # Delete the lock
            self.destroyLock(key)
        finally:
            self.thread_lock.release()

    def contextHasLock(self, ctx, key):
        key = self.cleanKey(key)

        self.thread_lock.acquire()
        try:
            try:
                lock = self.permanent_locks[key]
            except KeyError:
                return False
            if not lock.isValid():
                self.destroyLock(key)
                return False
            return lock.contextHasLock(ctx)
        finally:
            self.thread_lock.release()

    def service_list(self, context):
        """
        List of the locks, each item is (key, cookie). cookie may be an
        empty string if the lock was acquired but the session is closed
        or has expired without releasing the lock.
        """
        self.thread_lock.acquire()
        try:
            lock_list = []
            for key, lock in self.permanent_locks.iteritems():
                if isinstance(lock, PersistentLock):
                    if lock.isValid():
                        lock_list.append((key, lock.getSession().cookie))
                elif isinstance(lock, ComponentLock):
                    lock_list.append((key, lock.getComponentName()))
                else:
                    lock_list.append((key, "unknown"))
            return lock_list
        finally:
            self.thread_lock.release()

    def checkServiceCall(self, context, service_name):
        if not context.hasSession():
            service = "%s.%s()" % (self.name, service_name)
            raise LockError(tr("You need a session to call the %s service"), service)

