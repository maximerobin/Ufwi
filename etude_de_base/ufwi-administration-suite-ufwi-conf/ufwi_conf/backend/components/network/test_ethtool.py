#!/usr/bin/env python
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


from ethtool import Ethtool, NoSuchDevice

def test_ethtool_g():
    e = Ethtool('/usr/sbin/ethtool')
    e.ethtool_g('eth0')
    print e.g.result

def test_non_existent_g():
    e = Ethtool('/usr/sbin/ethtool')
    try:
        e.ethtool_g('no_such')
    except NoSuchDevice:
        print "device not found! (yippee)"
    else:
        assert False

def test_ethtool_S():
    e = Ethtool('/usr/sbin/ethtool')
    e.ethtool_S('eth0')
    print e.S.result

def test_non_existent_S():
    e = Ethtool('/usr/sbin/ethtool')
    try:
        e.ethtool_S('no_such')
    except NoSuchDevice:
        print "device not found! (yippee)"
    else:
        assert False

if __name__ == '__main__':
    test_ethtool_g()
    test_non_existent_g()
    test_non_existent_S()
    test_ethtool_S()

