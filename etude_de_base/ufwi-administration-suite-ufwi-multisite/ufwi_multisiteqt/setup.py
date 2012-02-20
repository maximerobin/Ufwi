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


from sys import argv

CLASSIFIERS = [
    'Intended Audience :: Developers',
    'Development Status :: 4 - Beta',
    'License :: OSI Approved :: GNU General Public License (GPL)',
    'Operating System :: OS Independent',
    'Natural Language :: English',
    'Programming Language :: Python',
]

PACKAGES = ('ew4_multisite', 'ew4_multisite.ui')

def main():
    if "--setuptools" in argv:
        argv.remove("--setuptools")
        from setuptools import setup
        use_setuptools = True
    else:
        from distutils.core import setup
        use_setuptools = False

    long_description = "Edenwall multisite interface"

    install_options = {
        "name": "ew4-multisite-qt",
        "version": "1.0",
        "url": "http://inl.fr/",
        "download_url": "",
        "license": "License",
        "author": "Laurent Defert",
        "description": "Edenwall multisite interface",
        "long_description": long_description,
        "classifiers": CLASSIFIERS,
        "packages": PACKAGES,
        "scripts": ("ew4-multisite-qt",),
    }
    if use_setuptools:
        install_options["install_requires"] = ["nufaceqt>=3.0", "PyQt4>=4.4"]
    setup(**install_options)

if __name__ == "__main__":
    main()

