# $Id$

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

IS_CHANGEABLE = \
CHANGEABLE, CHANGE_DISCOURAGED, NOT_CHANGEABLE = \
"CHANGEABLE CHANGE_DISCOURAGED NOT_CHANGEABLE".split()

from ufwi_rpcd.common.validators import check_hostname

class HostnameCfg(object):
    """
    Config object for hostname

    Changelog:
    0 -> 1: quick work, not yet going to AbstractConf
    (would be uniform with other ufwi_conf.common but overkill)
    * add a version number
    * support downgrade
    * change boolean 'frozen' -> multivalued 'changeable'

    """
    DATASTRUCTURE_VERSION = 1
    def __init__(self, hostname, changeable, received_version):
        self.hostname = unicode(hostname)
        if changeable not in IS_CHANGEABLE:
            raise ValueError(
                "Unexpected value for 'changeable': %r" % changeable
                )
        self.changeable = changeable
        self.received_version = received_version

    def setHostname(self, hostname):
        self.hostname = unicode(hostname)

    def serialize(self):
        serialized = {}
        serialized['hostname'] = self.hostname
        if self.received_version == 0:
            serialized['frozen'] = self.changeable != CHANGEABLE
        else:
            serialized['changeable'] = self.changeable
        return serialized

    def isValid(self):
        return check_hostname(self.hostname)

def deserialize(serialized):
    hostname = serialized['hostname']
    received_version = serialized.get('version', 0)
    if received_version == 1:
        return HostnameCfg(hostname, serialized['changeable'], 1)

    #might support next versions
    changeable = serialized.get('changeable', None)
    if changeable is None:
        compat_changeable = serialized.get('frozen', None)
        if compat_changeable:
            changeable = CHANGE_DISCOURAGED
        else:
            changeable = CHANGEABLE

    return HostnameCfg(hostname, changeable, received_version)

