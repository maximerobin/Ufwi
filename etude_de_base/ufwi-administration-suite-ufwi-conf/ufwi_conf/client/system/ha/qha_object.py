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


from ufwi_rpcd.common import EDENWALL
if EDENWALL:
    from ufwi_conf.common.ha_cfg import HAConf

from ufwi_conf.client.qt import QConfigObject
from ufwi_conf.common.ha_statuses import ENOHA

class QHAObject(QConfigObject):
    def __init__(self, parent=None):
        QConfigObject.__init__(self, HAConf.deserialize, 'hacfg', 'setHACfg',
            parent=parent)

    def has_ha(self):
        return self.cfg is not None and self.cfg.ha_type != ENOHA

