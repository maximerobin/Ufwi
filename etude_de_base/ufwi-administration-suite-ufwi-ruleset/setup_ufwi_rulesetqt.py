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
from sys import argv

CLASSIFIERS = [
    'Intended Audience :: Developers',
    'Development Status :: 4 - Beta',
    'License :: OSI Approved :: GNU General Public License (GPL)',
    'Operating System :: OS Independent',
    'Natural Language :: English',
    'Programming Language :: Python',
]

PACKAGES = ('ufwi_rulesetqt', 'ufwi_rulesetqt.rule')

def main():
    if "--setuptools" in argv:
        argv.remove("--setuptools")
        from setuptools import setup
        use_setuptools = True
    else:
        from distutils.core import setup
        use_setuptools = False

    ufwi_ruleset = load_source("version", path.join("ufwi_ruleset", "version.py"))

    long_description = open('README').read() + open('ChangeLog').read()

    install_options = {
        "name": "ufwi_rulesetqt",
        "version": ufwi_ruleset.VERSION,
        "url": ufwi_ruleset.WEBSITE,
        "download_url": ufwi_ruleset.WEBSITE,
        "license": ufwi_ruleset.LICENSE,
        "author": "Victor Stinner",
        "description": "Netfilter configuration backend",
        "long_description": long_description,
        "classifiers": CLASSIFIERS,
        "packages": PACKAGES,
        "scripts": ("ufwi_ruleset_qt",),
    }
    if use_setuptools:
        install_options["install_requires"] = ["ufwi_ruleset>=3.0", "PyQt4>=4.4"]
    setup(**install_options)

if __name__ == "__main__":
    main()

