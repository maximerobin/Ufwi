#!/usr/bin/env python
# $Id: setup.py 671 2004-08-22 21:02:29Z md $
	
	import sys
	if "--setuptools" in sys.argv:
	sys.argv.remove("--setuptools")
	from setuptools import setup
	else:
	from distutils.core import setup
	
	# Open IPy.py to read version
	from imp import load_source
	from os.path import join as path_join, dirname
	filename = path_join(dirname(__file__), "ufwi-authd-cmd", "version.py")
	command = load_source("", filename)
	
	LONG_DESCRIPTION = "Command line program to control ufwi-authd through UNIX socket"
	CLASSIFIERS = [
	'Development Status :: 5 - Production/Stable',
	'Intended Audience :: System Administrators',
	'Environment :: Console',
	'Topic :: System :: Networking',
	'License :: OSI Approved :: GNU General Public License (GPL)',
	'Operating System :: OS Independent',
	'Natural Language :: English',
	'Programming Language :: Python']
	
	setup(name="ufwi-authd-cmd",
	version=command.VERSION,
	description="Command line program to control ufwi-authd",
	long_description=LONG_DESCRIPTION,
	author="Victor Stinner",
	maintainer="Victor Stinner",
	maintainer_email="victor.stinner AT inl.fr",
	license=command.LICENSE,
	url=command.WEBSITE,
	download_url=command.WEBSITE,
	classifiers= CLASSIFIERS,
	scripts=["scripts/ufwi-authd-cmd"],
	packages=["ufwi-authd-cmd"],
	package_dir={"ufwi-authd-cmd": "ufwi-authd-cmd"})
