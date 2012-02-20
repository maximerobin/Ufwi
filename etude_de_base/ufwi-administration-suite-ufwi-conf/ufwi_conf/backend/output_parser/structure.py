
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

import re
from ufwi_conf.backend.output_parser.errors import NoMatch

class Field(object):
    def __init__(self, regex, is_multiline):
        self.regex = re.compile(regex)
        self.is_multiline = is_multiline

class OutputStructure(object):
    WHITESPACE = re.compile(r'^\s*$')
    def __init__(self, title_regex, errors={}):
        """
        In case of nested OutputStructures, only define errors at top level
        """
        self.title_regex = title_regex
        self.title_re = re.compile(title_regex)
        self.errors = errors
        self.fields = {}
        self.sections = frozenset()

    def addField(self, name, regex, multiline=False):
        self.fields[name] = Field(regex, multiline)

    def matchError(self, line, arg):
        for regex in self.errors.keys():
            if re.match(regex, line):
                raise self.errors[regex](arg)

    def matchTitle(self, line):
        if self.title_re.search(line):
            return True
        return False

    @staticmethod
    def matchWhiteSpace(line):
        if OutputStructure.WHITESPACE.search(line):
            return True
        return False

    def getField(self, line):
        for name, field in self.fields.iteritems():
            match = field.regex.search(line)
            if match:
                #errors here mean no regex groups was defined in the regex
                return name, match.groups()[0], field.is_multiline
        raise NoMatch("No name matched", line)
