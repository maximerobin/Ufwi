#coding: utf-8
"""
Copyright (C) 2010-2011 EdenWall Technologies
"""

from ufwi_rpcd.backend import ComponentError
from ufwi_rpcd.common.error import NUCONF
from ufwi_rpcd.common import tr
from ufwi_conf.common.error import NUCONF_HA

class HAError(ComponentError):
    def __init__(self, *args, **kw):
        ComponentError.__init__(self, NUCONF, NUCONF_HA, *args, **kw)

class InvalidConf(HAError):
    def __init__(self, *args, **kw):
        HAError.__init__(self, HA_INVALID_CONF, *args, **kw)

class CreateHaFailed(HAError):
    def __init__(self, *args, **kw):
        HAError.__init__(self, CREATE_HA_FAILED, *args, **kw)

class InvalidCallDone(HAError):
    def __init__(self, *args, **kw):
        HAError.__init__(self, INVALID_CALL_DONE, *args, **kw)

class IncoherentState(HAError):
    def __init__(self, *args, **kw):
        HAError.__init__(self, INCOHERENT_STATE, *args, **kw)

class InvalidHostname(HAError):
    def __init__(self, *args, **kw):
        HAError.__init__(self, INVALID_HOSTNAME, *args, **kw)

class DuplicateCall(HAError):
    def __init__(self, *args, **kw):
        HAError.__init__(self, DUPLICATE_CALL, *args, **kw)

class SecondaryFailedToApply(HAError):
    def __init__(self, errors):
        """
        provide errors as a list of strings
        """
        strerrors = "\n - ".join(errors)
        text = tr(
                "Application error occurred on secondary appliance. "
                "Please read logs on the secondary appliance."
                )
        HAError.__init__(
                self,
                SECONDARY_FAILED_TO_APPLY,
                "%s\n - %s" % (text, strerrors)
                )

class InitScriptConfigError(HAError):
    def __init__(self, *args, **kw):
        HAError.__init__(self, INITSCRIPT_CONFIG, *args, **kw)


# Error codes:
HA_INVALID_CONF = 1
CREATE_HA_FAILED = 2
INVALID_CALL_DONE = 3
INCOHERENT_STATE = 4
INVALID_HOSTNAME = 5
DUPLICATE_CALL = 6
SECONDARY_FAILED_TO_APPLY = 7
INITSCRIPT_CONFIG = 8
