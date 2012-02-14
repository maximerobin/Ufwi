
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

import platform
from sys import argv
from os.path import abspath

from PyQt4.QtGui import QMessageBox

from ufwi_rpcd.common import tr
from ufwi_rpcd.common.process import createProcess, ProcessError

def startEAS(logger, args = []):
    if platform.system() == 'Windows':
        import _winreg
        regkey = 'SOFTWARE\\Edenwall Technologies\\EAS\\'
        keyname = 'BinPath'
        key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, regkey)
        eas_bin = _winreg.QueryValueEx(key, keyname)[0]
    else:
        eas_bin = abspath(argv[0])

    try:
        # Append arguments
        eas_cmd = [eas_bin] + args
        createProcess(logger, eas_cmd)
    except ProcessError:
        QMessageBox.critical(None,
            tr("Edenwall Administration Suite"),
            tr("Please install Edenwall Administration Suite before performing this operation"))

