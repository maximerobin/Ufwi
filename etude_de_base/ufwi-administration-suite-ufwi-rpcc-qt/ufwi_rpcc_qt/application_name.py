# -*- coding: utf-8 -*-

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


from ufwi_rpcd.common import tr

# An application can have multiple names:
#  - Python module path (a.b.c)
#  - directory name,
#  - name used as client name in a Rpcd session
#  - etc.

APPLICATION_NAME = {}
for text, keys in {
    tr('EdenWall Administration Suite'): ('eas',),
    tr('Summary'): ('console_edenwall.homepage',),
    tr('System'): ('nuconf.client.system',),
    tr('Services'): ('nuconf.client.services',),
    tr('EAS Users Management'): ('ufwi_rpcd_admin', 'ufwi_rpcd-admin'),
    tr('Firewall'): ('nuface', 'nufaceqt'),
    tr('Logs'): ('nulog.client.qt',),
    tr('Graphs'): ('nugraph.client',),
    tr('PKI'): ('nupki.qt',),
    tr('Central Management'): ('ew4_multisite',),
    tr('Console Client'): ('ufwi_rpcd_client',),
    tr('Streaming'): ('streaming',),
    tr('Protocol Analysis'): ('nudpi.client.qt',),
}.iteritems():
    for key in keys:
        APPLICATION_NAME[key] = text

