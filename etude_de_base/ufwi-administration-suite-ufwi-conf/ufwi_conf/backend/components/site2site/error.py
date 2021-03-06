# -*- coding: utf-8 -*-
"""
$Id$


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
from ufwi_conf.common.error import NUCONF_SITE2SITE

class Site2SiteError(ComponentError):
    def __init__(self, *args, **kw):
        ComponentError.__init__(self, NUCONF, NUCONF_SITE2SITE, *args, **kw)

class FingerprintNotFound(Site2SiteError):
    def __init__(self, *args, **kw):
        Site2SiteError.__init__(self, FP_NOT_FOUND, *args, **kw)

class DefaultRouteError(Site2SiteError):
    def __init__(self, *args, **kw):
        Site2SiteError.__init__(self, DEFAULT_ROUTE_ERROR, *args, **kw)

class InvalidConfError(Site2SiteError):
    def __init__(self, *args, **kw):
        Site2SiteError.__init__(self, INVALID_CONF, *args, **kw)

# Error codes:
FP_NOT_FOUND = 1
DEFAULT_ROUTE_ERROR = 2
INVALID_CONF = 3
