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

setup(name="Rpcd-MultiSite",
    description="Multisite modules for Rpcd",
    author="INL",
    author_email="romain@inl.fr",
    packages=['ufwi_multisite',
              'ufwi_multisite.',
              'ufwi_multisite.master',
              'ufwi_multisite.master.common',
              'ufwi_multisite.master.nuface',
              'ufwi_multisite.master.update',
              'ufwi_multisite.slave',
             ],
)

