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


from doctest import testfile, ELLIPSIS, testmod
from sys import exit, path as sys_path
from os.path import dirname

def testDoc(filename, name=None):
    print "--- %s: Run tests" % filename
    failure, nb_test = testfile(
        filename, optionflags=ELLIPSIS, name=name)
    if failure:
        exit(1)
    print "--- %s: End of tests" % filename

def importModule(name):
    mod = __import__(name)
    components = name.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod

def testModule(name):
    print "--- Test module %s" % name
    module = importModule(name)
    failure, nb_test = testmod(module)
    if failure:
        exit(1)
    print "--- End of test"

def main():
    nuface_dir = dirname(__file__)
    sys_path.append(nuface_dir)

    # Test documentation in doc/*.rst files
#    testDoc('doc/nuface.rst')

    # Test documentation of some functions/classes
    testModule("ufwi_log.core.datasource")

if __name__ == "__main__":
    main()

