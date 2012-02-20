#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

components = """
access
antispam
antivirus
auth_cert
bind
contact
dhcp
exim
ha
ha.primary
ha.secondary
hostname
hosts
httpout
ids_ips
license
network
ntp
nuauth
nuauth_command
ufwi_conf_component
openvpn
quagga
resolv
snmpd
squid
status
supervisor
supervisor.correctors
syslog_export
system
system_info
update
site2site
tools
""".split()

PACKAGES = (
    'ufwi_conf.backend',
    'ufwi_conf.backend.output_parser',
    'ufwi_conf.backend.components',
)
PACKAGES += tuple(['ufwi_conf.backend.components.%s' % comp for comp in components])

def main():
    if "--setuptools" in argv:
        argv.remove("--setuptools")
        from setuptools import setup
        use_setuptools = True
    else:
        from distutils.core import setup
        use_setuptools = False

    ufwi_conf = load_source("version", path.join("ufwi_conf", "version.py"))

    long_description = open('README').read() + open('ChangeLog').read()

    install_options = {
        "name": ufwi_conf.PACKAGE,
        "version": ufwi_conf.VERSION,
        "url": ufwi_conf.WEBSITE,
        "download_url": ufwi_conf.WEBSITE,
        "license": ufwi_conf.LICENSE,
        "author": "Francois Toussenel, Michael Scherrer, Feth Arezki, Pierre-Louis Bonicoli",
        "description": "System configuration backend and frontend",
        "long_description": long_description,
        "classifiers": CLASSIFIERS,
        "packages": PACKAGES,
    }
    if use_setuptools:
        install_options["install_requires"] = ["IPy>=0.42"]
    setup(**install_options)

if __name__ == "__main__":
    main()

