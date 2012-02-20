
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

from subprocess import STDOUT, PIPE

from ufwi_rpcd.common.logger import LoggerChild
from ufwi_rpcd.backend.process import runCommand

from ufwi_conf.backend.output_parser.errors import NoMatch, ParserError
from ufwi_conf.backend.output_parser.structure import OutputStructure

class CmdError(Exception):
    pass

class OutputError(ParserError):
    pass

class NotAllowed(Exception):
    pass

class Parser(LoggerChild):
    def __init__(self, output_structure, cmd, parent_logger, cmd_timeout=5):
        LoggerChild.__init__(self, parent_logger)
        self.output_structure = output_structure
        self.cmd = cmd
        self.cmd_timeout = cmd_timeout
        self.last_matched_field = None

    def reset(self):
        self.title_set = {
            self.output_structure: False
        }

    def matchTitle(self, section, result, line):
        if not self.title_set[section] and section.matchTitle(line):
            result['Section_title'] = line
            self.title_set[section] = True
            return True

        if not self.title_set[section]:
            raise OutputError('expected title, got "%s"' % line, line)

        return False

    def matchSection(self, containing_section, children, line):
        for section in children:
            name, current = section
            match = current.title_re.search(line)
            if match:
                return name, current

        #This exception exits current section in parseFlow
        raise NoMatch('unexpected "%s" in section "%s"' % (line, containing_section.title_regex), line)

    def matchField(self, section, result, line):
        try:
            name, content, is_multiline = section.getField(line)
        except NoMatch:
            return False

        if is_multiline:
            self.last_matched_field = name
            result[name] = [content]
        else:
            self.last_matched_field = None
            result[name] = content
        return True

    def parseLine(self, section, result, children, line, arg):
        """
        Parses a line.
        args:
        -the section this line is expected to belong to
        -the result dict in which the result should be stored
        -the children sections of the section mentioned before
        -the line to parse
        -the argument that we (as Parser.fetch()) got, and that might be useful for debugging.

        returns:
        -None: the line was parsed, the result stored into result
        -(name, section): the line was detected as the title of an inner section

        raises:
        NoMatch: the line does not belong to this section
        """
        #Ignore whitespace
        if OutputStructure.matchWhiteSpace(line):
            return None

        #We propagate exceptions:
        self.output_structure.matchError(line, arg)

        #We propagate exceptions:
        if self.matchTitle(section, result, line):
            self.last_matched_field = None
            return None

        if self.matchField(section, result, line):
            return None


        #We propagate exceptions:
        try:
            return self.matchSection(section, children, line)
        except NoMatch, err:
            if self.last_matched_field is None:
                raise
            result[self.last_matched_field].append(line)

    def parseFlow(self, flow, arg):
        """
        returns a recursive dict with the parsed data
        """
        self.reset()

        current_result = base_result = {}
        results_stack = [base_result]
        sections_stack = [self.output_structure]
        children_stack = [set(self.output_structure.sections)]

        for line in flow:
            line = line.strip()
            parsed = False

            while not parsed:
                if len(sections_stack) == 0:
                    raise OutputError("parser encountered an error: out of any section while parsing '%s' (command was '%s')" % (line, self.cmd), line)
                current_section = sections_stack[-1]
                current_result = results_stack[-1]
                current_child = children_stack[-1]

                try:
                    parse_result = self.parseLine(
                        current_section,
                        current_result,
                        current_child,
                        line,
                        arg)
                except NoMatch:
                    #exit current section
                    self.last_matched_field = None
                    s = sections_stack.pop()
                    results_stack.pop()
                    children_stack.pop()
                    #reparse
                    continue

                parsed = True

                if parse_result is None:
                    continue

                #enter new section
                self.last_matched_field = None
                name, other_section = parse_result
                new_result = {}
                current_result[name] = new_result
                results_stack.append(new_result)
                self.title_set[other_section] = True
                sections_stack.append(other_section)
                children_stack.append(set(other_section.sections))

        return base_result

    def runCmd(self, cmd_line, arg):
        cmd_words = cmd_line.split()

        cmd = []
        for word in cmd_words:
            if word == "%%arg%%":
                word = arg
            cmd.append(word)

        try:
            process, retcode = runCommand(self, cmd, timeout = self.cmd_timeout, stdout=PIPE, stderr=STDOUT)
            if retcode != 0:
                raise CmdError(retcode)
            return process.stdout

        except OSError, err:
            self.error("Problem running '%s':\n%s", cmd_line, err)
            raise err

    def fetch(self, iface_name):
        flow = self.runCmd(self.cmd, iface_name)
        return self.parseFlow(flow, iface_name)

