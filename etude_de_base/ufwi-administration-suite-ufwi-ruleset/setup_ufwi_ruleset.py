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


from imp import load_source
from os import path

CLASSIFIERS = [
    'Intended Audience :: Developers',
    'Development Status :: 4 - Beta',
    'License :: OSI Approved :: GNU General Public License (GPL)',
    'Operating System :: OS Independent',
    'Natural Language :: English',
    'Programming Language :: Python',
]

PACKAGES = (
    'ufwi_ruleset',
    'ufwi_ruleset.common',
    'ufwi_ruleset.iptables',
    'ufwi_ruleset.forward',
    'ufwi_ruleset.forward.resource',
    'ufwi_ruleset.forward.rule',
    'ufwi_ruleset.localfw',
)

def main():
    from distutils.core import setup
    from distutils.command.install import INSTALL_SCHEMES

    # Install scripts (ufwi_ruleset) in /usr/sbin instead of /usr/bin
    INSTALL_SCHEMES['unix_prefix']['scripts'] = '$base/sbin'

    ufwi_ruleset = load_source("version", path.join("ufwi_ruleset", "version.py"))

    long_description = open('README').read() + open('ChangeLog').read()

    setup(
        name=ufwi_ruleset.PACKAGE,
        version=ufwi_ruleset.VERSION,
        url=ufwi_ruleset.WEBSITE,
        download_url=ufwi_ruleset.WEBSITE,
        license=ufwi_ruleset.LICENSE,
        author="Victor Stinner",
        description="Netfilter configuration backend",
        long_description=long_description,
        classifiers=CLASSIFIERS,
        packages=PACKAGES,
        scripts=("scripts/ufwi_ruleset",),
    )

if __name__ == "__main__":
    main()

