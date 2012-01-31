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


from ConfigParser import RawConfigParser
import os
import sys

def open_element(type, **args):
    s = '<%s' % type
    for key, value in args.iteritems():
        s += ' %s="%s"' % (key, value)
    s += '>'
    sys.stdout.write(s)

def close_element(type):
    sys.stdout.write('</%s>' % type)

def print_values(config, section):
    for key, value in config.items(section):
        open_element('data', name=key)
        sys.stdout.write(value)
        close_element('data')

def print_sections(config):
    for section in config.sections():
        open_element('config_elt', name=section)
        print_values(config, section)
        close_element('config_elt')

def main(argv):
    if len(argv) < 2:
        print 'Syntax: %s storage_path' % argv[0]
        return 1

    open_element('edenwall', version=1)
    for root, dirs, files in os.walk(argv[1]):

        for file in files:
            config = RawConfigParser()
            config.readfp(open(os.path.join(root, file)))
            open_element('config_elt', name=file)
            print_sections(config)
            close_element('config_elt')

    close_element('edenwall')
    return 0

if __name__ == '__main__':
    from sys import argv, exit
    exit(main(argv))
