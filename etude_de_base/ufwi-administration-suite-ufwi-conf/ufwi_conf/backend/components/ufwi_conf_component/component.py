# -*- coding: utf-8 -*-
"""
Copyright (C) 2010-2011 EdenWall Technologies
Written by Pierre-Louis Bonicoli <bonicoli AT inl.fr>

$Id$
"""
from ufwi_rpcd.core.lock import AlreadyAcquired

from ufwi_rpcd.backend import Component

class NuConfComponent(Component):
    """
    Component to manage the NTP server, and synchronize the time
    """
    NAME = "ufwi_conf"
    VERSION = "1.0"
    API_VERSION = 2

    REQUIRES = ('lock', )

    CONFIG_DEPENDS = ()

    ROLES = {
        'ufwi_conf_write': set(('takeWriteRole', 'endUsingWriteRole')),
    }

    def init(self, core):
        self.core = core

    def service_takeWriteRole(self, context):
        """
        Acquire the write lock. Return True on success, False if the lock owned
        by someone else.
        """
        try:
            self.core.lock_manager.acquire(context, 'ufwi_conf_write')
        except AlreadyAcquired, err:
            if err.by_other:
                return False
            else:
                return True
        else:
            return True

    def service_endUsingWriteRole(self, context):
        """
        Release the write lock. Raise a LockError if the lock is not acquired
        or acquired by somone else.
        """
        self.core.lock_manager.release(context, 'ufwi_conf_write')

