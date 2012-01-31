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

from ufwi_rpcd.python import backportXmlrpclib
backportXmlrpclib()

from ufwi_rpcd.common.unicode_stdout import installUnicodeStdout
installUnicodeStdout()
from ufwi_rpcd.common import tr
from ufwi_rpcd.common import is_pro
from ufwi_rpcd.client.error import RpcdError, SessionError
from ufwi_rpcd.client.base import (
    RpcdClientBase, Cookie,
    DEFAULT_HOST, DEFAULT_PORT, DEFAULT_PROTOCOL, KEEP_ALIVE_SECONDS)

if is_pro():
    SOFTWARE_MAIN_NAME = tr("EdenWall")
    CLIENT_SUITE_NAME = tr("Edenwall Administration Suite")
    CLIENT_SUITE_SHORTNAME = tr("EAS")
else:
    SOFTWARE_MAIN_NAME = tr("NuFirewall")
    CLIENT_SUITE_NAME = tr("NuFirewall Administration Suite")
    CLIENT_SUITE_SHORTNAME = tr("NuFW-AS")

