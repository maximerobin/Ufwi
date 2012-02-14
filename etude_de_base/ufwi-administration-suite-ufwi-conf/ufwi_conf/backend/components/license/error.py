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
from ufwi_conf.common.error import NUCONF_LICENSE

class NuConfError(ComponentError):
    def __init__(self, *args, **kw):
        ComponentError.__init__(self, NUCONF, NUCONF_LICENSE, *args, **kw)

# Error codes:
LICENSE_NOT_CONFIGURED = 1
LICENSE_GETID_ERROR = 2
LICENSE_BAD_SIG = 3
LICENSE_NOT_FOR_ME = 4
LICENSE_GET_LICENSES_ERROR = 5
LICENSE_MISSING_FIELDS = 6
LICENSE_DPI_ACTIVATION_ERROR = 7
