#!/usr/bin/env python

# test command: python setup.py install --no-compile --root=./debian/ufwi_rpcd

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
from distutils.command.install import INSTALL_SCHEMES
from ufwi_rpcd.core.version import VERSION, WEBSITE

INSTALL_SCHEMES['unix_prefix']['scripts'] = '$base/bin'

setup(name="ufwi-rpcd",
    version=VERSION,
    description="ufwi-rpcd components and service broker",
    author="INL",
    url=WEBSITE,
    author_email="chifflier@inl.fr",
    packages=['ufwi_rpcd',
              'ufwi_rpcd.backend',
              'ufwi_rpcd.common',
              'ufwi_rpcd.common.odict',
              'ufwi_rpcd.common.ssl',
              'ufwi_rpcd.core',
              'ufwi_rpcd.core.auth',
              'ufwi_rpcd.core.config',
              'ufwi_rpcd.core.users_config',
              'ufwi_rpcd.client',
              'ufwi_rpcd.python',
             ],
    scripts=['ufwi-rpcd.tac']
)

