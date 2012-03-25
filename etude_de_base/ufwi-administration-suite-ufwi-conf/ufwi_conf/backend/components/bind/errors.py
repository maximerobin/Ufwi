#coding: utf-8
"""
Copyright(C) 2010 EdenWall Technologies
$Id$
"""
from ufwi_rpcd.common.error import NUCONF
from ufwi_rpcd.backend import ComponentError
from ufwi_conf.common.error import NUCONF_BIND

class BindError(ComponentError):
    def __init__(self, *args, **kw):
        ComponentError.__init__(self, NUCONF, NUCONF_BIND, *args, **kw)

class DNSError(BindError):
    def __init__(self, *args, **kw):
        BindError.__init__(self, DNS_ERROR, *args, **kw)

# Error codes:
DNS_ERROR = 1

