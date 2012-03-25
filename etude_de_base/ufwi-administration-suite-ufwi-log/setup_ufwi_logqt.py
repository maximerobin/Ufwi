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
              'ufwi_log.client',
              'ufwi_log.client.qt',
              'ufwi_log.client.qt.args',
              'ufwi_log.client.qt.fetchers',
              'ufwi_log.client.qt.ui',
              'ufwi_log.client.qt.user_settings',
              'ufwi_log.client.qt.views',
              'ufwi_log.client.qt.widgets',
             ],
    scripts=("ufwi_logqt/ufwi_log_qt",),
)

