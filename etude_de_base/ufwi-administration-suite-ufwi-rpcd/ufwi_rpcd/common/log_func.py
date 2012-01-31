
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

from logging import CRITICAL, ERROR, WARNING, INFO, DEBUG
from ufwi_rpcd.common.tools import minmax

LOG_LEVELS = {
    'CRITICAL': CRITICAL,
    'ERROR': ERROR,
    'WARNING': WARNING,
    'INFO': INFO,
    'DEBUG': DEBUG,
}

def getLogLevel(name, default=ERROR):
    name = name.upper()
    return LOG_LEVELS.get(name, default)

def getLogFunc(logger, level):
    if level == CRITICAL:
        return logger.critical
    elif level == ERROR:
        return logger.error
    elif level == WARNING:
        return logger.warning
    elif level == INFO:
        return logger.info
    elif level == DEBUG:
        return logger.debug
    else:
        return logger.error

def changeLogLevel(level, delta):
    return minmax(DEBUG, level + delta*10, CRITICAL)

