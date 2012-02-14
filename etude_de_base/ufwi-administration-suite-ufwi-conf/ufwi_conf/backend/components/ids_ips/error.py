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
from ufwi_conf.common.error import NUCONF_IDS_IPS

class IdsIpsError(ComponentError):
    def __init__(self, *args, **kw):
        ComponentError.__init__(self, NUCONF, NUCONF_IDS_IPS, *args, **kw)

# Error codes:
IDS_IPS_NO_MINMAX_SCORES_ERROR = 11
IDS_IPS_SELECT_RULES_ERROR = 12
IDS_IPS_SELECTED_RULES_COUNTS_ERROR = 13
IDS_IPS_TOTAL_RULES_COUNTS_ERROR = 14
IDS_IPS_START_ERROR = 15
IDS_IPS_STOP_ERROR = 16
IDS_IPS_FIREWALL_ERROR = 17
IDS_IPS_NO_LOGS = 18
IDS_IPS_INVALID_CONFIG = 19
