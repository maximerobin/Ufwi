"""
Copyright (C) 2007-2011 EdenWall Technologies
Written by Pierre Chifflier <p.chifflier AT inl.fr>

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

$Id$
"""

from os import unlink
from os.path import exists

# new version of xmlrpclib from Python trunk (2.7)
# supporting HTTP(S)/1.1 (keep-alive)
from ufwi_rpcd.python import backportXmlrpclib
backportXmlrpclib()

_REAPPLY_STAMP = '/var/lib/ufwi-rpcd/ufwi_conf/FORCE_CONFIG_REAPPLICATION'
def mustreapply():
    return exists(_REAPPLY_STAMP)

def del_reapply_stamp():
    if mustreapply():
        unlink(_REAPPLY_STAMP)

