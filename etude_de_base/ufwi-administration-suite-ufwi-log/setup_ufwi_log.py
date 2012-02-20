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


from distutils.core import setup

setup(name="ufwi-log",
    version="3.0",
    description="Graphical firewall log analysis interface",
    author="INL",
    url="http://ufwi.org/",
    packages=['ufwi_log',
              'ufwi_log.core',
              'ufwi_log.core.reporting',
              'ufwi_log.core.database',
              'ufwi_log.core.database.request',
              'ufwi_log.core.database.request.mysql',
              'ufwi_log.core.database.request.pgsql'
             ],
)

