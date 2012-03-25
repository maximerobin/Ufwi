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


from __future__ import with_statement
import os
from ufwi_conf.common.ha_statuses import HA_STATUS, ENOHA, PRIMARY, SECONDARY

CONFIG_HATYPE_NAME = 'ha_type'
def readHaType(directory):
    try:
        with open(os.path.join(directory, CONFIG_HATYPE_NAME)) as f:
            ha_type = f.readline().strip()
            if not ha_type:
                return ENOHA
            elif ha_type not in HA_STATUS:
                raise Exception("Invalid HA type: %s" % unicode(ha_type))
    except IOError:
        return ENOHA

    return ha_type

def saveHaType(directory, ha_type):
    try:
        f = open(os.path.join(directory, CONFIG_HATYPE_NAME), 'w')
    except IOError:
        return False
    else:
        f.write(ha_type + '\n')
        return True

