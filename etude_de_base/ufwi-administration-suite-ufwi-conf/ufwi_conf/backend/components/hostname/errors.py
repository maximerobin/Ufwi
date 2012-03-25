#coding: utf-8
"""
Copyright(C) 2010 EdenWall Technologies
$Id$
"""
from ufwi_rpcd.common.error import NUCONF
from ufwi_rpcd.backend import ComponentError
from ufwi_conf.common.error import NUCONF_HOSTNAME

class HostnameError(ComponentError):
    def __init__(self, *args, **kw):
        ComponentError.__init__(self, NUCONF, NUCONF_HOSTNAME, *args, **kw)

class BadNameError(HostnameError):
    def __init__(self, *args, **kw):
        HostnameError.__init__(self, BADNAME_ERROR, *args, **kw)

_FROZEN_EXPLANATION = """\
The name of a high availability cluster member cannot be changed anymore \
after the cluster has been setup"""
class NameFrozenError(HostnameError):
    def __init__(self):
        HostnameError.__init__(self, NAME_FROZEN_ERROR, _FROZEN_EXPLANATION)

# Error codes:
BADNAME_ERROR = 1
NAME_FROZEN_ERROR = 2

