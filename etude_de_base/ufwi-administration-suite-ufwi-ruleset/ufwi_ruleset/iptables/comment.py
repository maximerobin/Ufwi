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

def comment(comment, empty_line="before", extra=None):
    if empty_line == "before":
        yield u""
    line = u"# %s" % comment
    length = len(comment)
    yield line
    yield u"# " + u"-" * length
    if extra:
        for line in extra.splitlines():
            yield u"# %s" % line
    if empty_line == "after":
        yield u""

def longComment(text):
    yield u""
    borders = u"#" + u"#" * (len(text) + 3)
    yield borders
    yield u"# %s #" % text
    yield borders

def closeComment(text):
    yield u"# " + u"-" * len(text)

