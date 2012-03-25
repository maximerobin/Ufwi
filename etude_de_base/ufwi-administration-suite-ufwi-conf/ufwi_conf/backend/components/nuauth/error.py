# -*- coding: utf-8 -*-
"""
Copyright(C) 2010 EdenWall Technologies
$Id$
"""
from ufwi_rpcd.common.error import NUCONF
from ufwi_rpcd.backend import ComponentError
from ufwi_conf.common.error import NUCONF_NUAUTH

class NuauthException(ComponentError):
    def __init__(self, *args, **kw):
        ComponentError.__init__(self, NUCONF, NUCONF_NUAUTH, *args, **kw)

class NoSuchUser(NuauthException):
    def __init__(self, username):
        NuauthException.__init__(self, NO_SUCH_USER, "%s", username)

class NoSuchGroup(NuauthException):
    def __init__(self, groupname):
        NuauthException.__init__(self, NO_SUCH_GROUP, "%s", groupname)

class AuthError(NuauthException):
    def __init__(self, message):
        NuauthException.__init__(self, AUTH_ERROR, message)

class GetentError(NuauthException):
    def __init__(self, username):
        NuauthException.__init__(self, GETENT_UNKNOWN_ERROR, "%s", username)

class NNDError(NuauthException):
    def __init__(self, message):
        NuauthException.__init__(self, NND_ERROR, message)

# Error codes:
NUAUTH_INVALID_CONF = 1
MAYBE_TEMPORARY_ERROR = 2
UNABLE_TO_FETCH_KEYTAB = 3
INVALID_KEYTAB = 4
NO_CACHE_DIR = 5
NO_SUCH_USER = 6
NO_SUCH_GROUP = 7
AUTH_ERROR = 8
GETENT_UNKNOWN_ERROR = 9
NO_MAPPING_EXISTS = 10
NND_ERROR = 11

