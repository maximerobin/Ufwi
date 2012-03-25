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


from nucentral.client import NuCentralClientBase
from sys import stderr, exit
import codecs
#from os import unlink
from os import system
from optparse import OptionParser
from nucentral.client import DEFAULT_HOST, DEFAULT_PROTOCOL

def escape(text):
    return text.replace(u"*", ur"\*")

class GenDoc:
    TITLE_CHARACTERS = {
        1: '+',
        2: '=',
        3: '-',
    }

    def __init__(self, output):
        options = self.parse_options()
        self.client = NuCentralClientBase(
            host=options.host,
            protocol=options.protocol)
        print (options.username, options.password)
        self.client.authenticate(
            unicode(options.username),
            unicode(options.password))
        self.output = output

    def parse_options(self):
        parser = OptionParser(usage="%prog [options] --username=USERNAME --password=PASSWORD")
        parser.add_option('-u', '--username',
            help="Username for NuCentral authentication",
            type="str", default=None)
        parser.add_option('-p', '--password',
            help="Password for NuCentral authentication",
            type="str", default=None)
        parser.add_option('--host',
            help="NuCentral server hostname or IP address (default: %s)" % DEFAULT_HOST,
            type="str", default=None)
        parser.add_option('--protocol',
            help="Protocol used to connect to NuCentral server (default: %s)" % DEFAULT_PROTOCOL,
            type="str", default=None)
        options, arguments = parser.parse_args()
        if not (options.username and options.password) \
        or arguments:
            parser.print_help()
            exit(1)
        return options

    def title(self, text, level):
        sep = self.TITLE_CHARACTERS[level] * len(text)
        if level == 1:
            print >>self.output, sep
        print >>self.output, text
        print >>self.output, sep
        print >>self.output

    def paragraph(self, text, new_line=True):
        self.write(text)
        if new_line:
            self.emptyLine()

    def write(self, text, prefixes=tuple()):
        if prefixes:
            prefix = prefixes[0]
        else:
            prefix = ''
        if isinstance(text, (str, unicode)):
            text = text.splitlines()
        for index, line in enumerate(text):
            if index < len(prefixes):
                prefix = prefixes[index]
            print >>self.output, prefix + line

    def listItem(self, text):
        self.write(text, (" * ", "   "))

    def pre(self, text, new_line=True):
        self.write(text, ("   ",))
        if new_line:
            self.emptyLine()

    def command(self, text):
        self.write(text, (".. ",))

    def emptyLine(self):
        print >>self.output

    def header(self):
        self.title("NuCentral documentation", 1)
        self.command("contents:: Summary")
        self.command("section-numbering::")
        self.emptyLine()

    def intro(self):
        self.title("Introduction", 2)
        self.paragraph("This document list all NuCentral components and services.")
        self.paragraph("Note: All component has a getComponentVersion() service but it's not repeated in each section of this document.")

    def main(self):
        self.header()
        self.intro()
        components = self.client.call('CORE', 'getComponentList')
        for component in components:
            self.documentComponent(component)

    def documentComponent(self, component):
        print >>stderr, " -> explore %s component" % component
        self.title(" %s component" % component, 2)
        doc = self.client.call('CORE', 'help', component)
        if doc:
            self.paragraph(doc)

        services = self.client.call('CORE', 'getServiceList', component)
        for service in services:
            self.documentService(component, service)
            self.emptyLine()

    def documentService(self, component, service):
        if service == "getComponentVersion":
            return
        prototype = self.client.call('CORE', 'prototype', component, service)
        self.title("%s service" % escape(prototype), 3)
        doc = self.client.call('CORE', 'help', component, service)
        self.paragraph(doc)

def main():
    filename_rst = 'nucentral.rst'
    filename_html = 'nucentral.html'
    output = codecs.open(filename_rst, 'w', 'utf8')
    doc = GenDoc(output)
    print "Explore NuCentral services..."
    doc.main()
    print "Convert reST to HTML..."
    exitcode = system("rst2html %s %s" % (filename_rst, filename_html))
    if exitcode:
        print "rst2html error!"
        exit(1)
    #unlink(filename_rst)
    print "Documentation written into %s" % filename_html

if __name__ == "__main__":
    main()

