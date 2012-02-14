#!/usr/bin/env python2.5
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


from ufwi_conf.backend.netcfg_autoconf import NetCfgAutoConf
from ufwi_conf.common.netcfg_rw import deserialize
from ufwi_rpcd.backend.logger import Logger

#SAMPLES = {'ip addr list': 'ip route list' }

def test_Netcfg():
    l = Logger("")
    n = NetCfgAutoConf(l)
    n.discover()
    s = n.serialize()
    netcfg =  deserialize(s)
    s2 = netcfg.serialize()

    assert s == s2, "buggy assertion"

if __name__ == "__main__":
    test_Netcfg()
