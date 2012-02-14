#coding: utf-8

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


from logging import getLogger
from PyQt4.QtGui import QApplication
from sys import argv, exit

from ufwi_rpcc_qt.start_eas import startEAS

def restart_eas(exit_code=0, logger=getLogger()):
    startEAS(logger, argv[1:])

    QApplication.exit()
    exit(exit_code)
