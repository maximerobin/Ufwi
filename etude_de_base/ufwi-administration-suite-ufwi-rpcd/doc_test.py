#!/usr/bin/python
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


from doctest import testfile, ELLIPSIS, testmod
from sys import exit, path as sys_path
from os import unlink
from os.path import dirname
from imp import load_source
import sys

def backup_modules(func):
    def decorated(*args, **kw):
        old_modules = dict(sys.modules)
        try:
            func(*args, **kw)
        finally:
            sys.modules = old_modules
    return decorated

@backup_modules
def testDoc(filename, name=None):
    print "--- %s: Run tests" % filename
    failure, nb_test = testfile(
        filename, optionflags=ELLIPSIS, name=name)
    if failure:
        exit(1)
    print "--- %s: End of tests" % filename

def importModule(name, filename=None):
    if filename:
        modname = name.split(".")[-1]
        return load_source(modname, filename)
    else:
        module = __import__(name)
        for part in name.split(".")[1:]:
            module = getattr(module, part)
        return module

@backup_modules
def testModule(name, filename=None):
    print "--- Test module %s" % name
    module = importModule(name, filename)
    failure, nb_test = testmod(module)
    if failure:
        exit(1)
    print "--- End of test"

def main():
    fusil_dir = dirname(__file__)
    sys_path.append(fusil_dir)

    # Disable xmlrpclib backport to avoid a bug in the unit tests
    from ufwi_rpcd.python import backportXmlrpclib
    backportXmlrpclib.done = True

    # Test documentation in doc/*.rst files
    testDoc('tests/try_finally.rst')

    # Test documentation of some functions/classes
    testModule("ufwi_rpcd.common.human")
    testModule("ufwi_rpcd.common.network")
    testModule("ufwi_rpcd.common.tools")
    testModule("ufwi_rpcd.common.transport")
    testModule("ufwi_rpcd.common.error")
    testModule("ufwi_rpcd.common.defer")
    testModule("ufwi_rpcd.common.ssl.checker")
    testModule("ufwi_rpcd.common.namedlist")
    testModule("ufwi_rpcd.common.process")
#    testModule("ufwi_rpcd.qt.tools")
    testModule("tools.ufwi_rpcd_client", "tools/ufwi_rpcd_client")
    # __import__('tools.ufwi_rpcd_client') compiles the Python file
    # to tools/ufwi_rpcd_clientc
    unlink("tools/ufwi_rpcd_clientc")

if __name__ == "__main__":
    main()

