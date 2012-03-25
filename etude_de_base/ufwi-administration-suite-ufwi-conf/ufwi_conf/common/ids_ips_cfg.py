
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

from ufwi_rpcd.common import tr
from ufwi_rpcd.common.abstract_cfg import AbstractConf

def none2float(arg, default=0.0):
    return default if arg is None else float(arg)

class IdsIpsCfg(AbstractConf):
    ATTRS = """
            enabled
            antivirus_enabled
            alert_threshold
            drop_threshold
            score_min
            score_max
            block
            networks
           """.split()

    DATASTRUCTURE_VERSION = 1

    def __init__(self, *args, **kwargs):
        self.enabled = bool(kwargs.get('enabled'))
        self.antivirus_enabled = bool(kwargs.get('antivirus_enabled'))
        self.alert_threshold = none2float(kwargs.get('alert_threshold'),
                                          default=200.0)
        self.drop_threshold = none2float(kwargs.get('drop_threshold'),
                                         default=300.0)
        self.score_min = none2float(kwargs.get('score_min'))
        self.score_max = none2float(kwargs.get('score_max'))
        self.block = bool(kwargs.get('block'))
        networks = kwargs.get('networks')
        self.networks = set() if networks is None else networks

    def isValidWithMsg(self):
        for network in self.networks:
            if network.version() == 6:
                return False, tr("IDS-IPS doesn't support IPv6 networks.")
        return True, None

    def setEnabled(self, state):
        self.enabled = bool(state)

    def setBlockingEnabled(self, state):
        self.block = bool(state)

    def setAntivirusEnabled(self, state):
        self.antivirus_enabled = bool(state)

