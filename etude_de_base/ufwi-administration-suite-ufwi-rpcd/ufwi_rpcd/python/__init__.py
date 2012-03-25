# Backport from Python trunk for Rpcd. The most important module is the
# new version xmlrpclib which supports HTTPS/1.1 (stay connected between two
# calls).

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


import sys

def backportXmlrpclib():
    # enable the httplib and xmlrpclib backports (from future Python
    # version 2.7) to get HTTP(S)/1.1 keep-alive
    if backportXmlrpclib.done:
        return
    backportXmlrpclib.done = True
    from ufwi_rpcd.python import httplib, xmlrpclib
    sys.modules['httplib'] = httplib
    sys.modules['xmlrpclib'] = xmlrpclib
backportXmlrpclib.done = False

#if sys.hexversion < 0x2060000:
#    # Enable the backport for Python 2.5
#    backportXmlrpclib.done = False
#else:
#    # Disable the backport: it doesn't work with Python 2.6
#    backportXmlrpclib.done = True

