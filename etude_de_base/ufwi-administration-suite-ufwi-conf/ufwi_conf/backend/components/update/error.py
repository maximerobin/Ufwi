# -*- coding: utf-8 -*-

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


from ufwi_rpcd.common.error import NUCONF
from ufwi_rpcd.backend import ComponentError
from ufwi_conf.common.error import NUCONF_UPDATE

class NuConfError(ComponentError):
    def __init__(self, *args, **kw):
        ComponentError.__init__(self, NUCONF, NUCONF_UPDATE, *args, **kw)

# Error codes:
UPDATE_NOT_TAR = 11
UPDATE_NO_UPGRADE_NUMBER = 12
UPDATE_UNPACK_ERROR = 21
UPDATE_BAD_SIG = 31
UPDATE_UNKNOWN_SIG = 32
UPDATE_CANNOT_READ_DESCRIPTION = 41
UPDATE_CHECKSUM_MISSING = 51
UPDATE_CHECKSUM_MISMATCH = 52
UPDATE_CANNOT_READ_FILE = 53
UPDATE_FILE_NAME_ERROR = 61
UPDATE_UNPACK_DATA_ERROR = 71
UPDATE_NO_SHORT_CHANGELOG = 81
UPDATE_DEPENDS_SYNTAX_ERROR = 83
UPDATE_NOT_CONFIGURED = 91
UPDATE_ALREADY_APPLIED_OR_DELETED = 101
UPDATE_CANNOT_APPLY_BECAUSE_DEPEND_NOT_APPLIED = 102
UPDATE_ALREADY_APPLIED = 103
UPDATE_BLACKLISTED = 104
UPDATE_WRONG_TARGET_TYPE = 105
UPDATE_REMOTE_DIRECTORY_NOT_FOUND = 111
UPDATE_REMOTE_UPGRADE_NOT_FOUND = 112
