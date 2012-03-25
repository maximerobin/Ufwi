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


import re
from ufwi_rpcd.common import tr

INDEX_VALIDITY = 1
INDEX_DAYS_LEFT = 2
INDEX_OPTION = 3
WARN_DAYS = 30
DPI_OPTION_NAME = "DPI"

def option_decode(code):
    if code == 'unlimited' or code == '':
        return tr('Unlimited')
    if code == 'utm':
        return tr('UTM')
    m = re.compile(r'^(\+?)([0-9]+)u$').search(code)
    if m:
        if m.group(1) == '+':
            return u'%s %s %s' % (
                tr('User Pack'), m.group(2), tr('users'))
        else:
            return u'EdenWall %s %s' % (m.group(2), tr('users'))
    return code
