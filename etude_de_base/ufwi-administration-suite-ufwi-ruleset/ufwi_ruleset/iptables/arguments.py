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

QUOTE_REGEX = re.compile(ur"[A-Za-z0-9# _:!-]+")

def quote(value):
    """
    Quote a string to use it as a shell argument.

    >>> print quote('10')
    10
    >>> print quote(u"a b")
    "a b"
    """
    value = unicode(value)
    if not QUOTE_REGEX.match(value):
        raise ValueError("Invalid characters in a shell argument: %s" % repr(value))
    if (" " in value) or ('"' in value):
        value = value.replace('"', '\\"')
        value = u'"%s"' % value
    return value

class Arguments:
    r"""
    Class to help writing a shell command: add spaces between arguments
    and escape arguments if needed.

    >>> print unicode(Arguments("-A", "OUTPUT", "-j", "ACCEPT"))
    -A OUTPUT -j ACCEPT
    >>> print unicode(Arguments("-j", "ULOG", "--ulog-prefix", 'test "quote"'))
    -j ULOG --ulog-prefix "test \"quote\""
    """
    def __init__(self, *arguments):
        self.arguments = [unicode(arg) for arg in arguments]

    def __add__(self, next):
        return Arguments(*(self.arguments + next.arguments))

    def __unicode__(self):
        return u' '.join( quote(arg) for arg in self.arguments)

    def __repr__(self):
        return u'<Arguments %r>' % unicode(self)

