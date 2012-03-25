
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

import sys
import re

from ufwi_rpcd.common.error import exceptionAsUnicode, formatTraceback
from ufwi_rpcd.common import tr
from ufwi_rpcd.client import RpcdError
from ufwi_rpcc_qt.html import (Html,
    htmlBold, htmlParagraph, htmlList, htmlPre, htmlItalic)

FILE_REGEX = re.compile('^File "(?P<filename>[^"]+)", line (?P<line>[0-9]+), in (?P<function>.+)$')

def truncateFilename(filename, maxlen, maxparts):
    """
    >>> truncateFilename('very_long_directory/name', 10, 3)
    '.../name'
    >>> truncateFilename('very_long_filename', 4, 3)
    '...name'
    >>> truncateFilename('aaa/123/ccc', 6, 3)
    '.../123/ccc'
    >>> truncateFilename('a/b/c/d/e', 100, 1)
    '.../e'
    """
    dirsep = '/'
    ellipsis = '...'
    parts = filename.split(dirsep)
    truncated = []
    for part in reversed(parts):
        if truncated:
            truncated.append(dirsep)
        if maxparts <= 0:
            truncated.append(ellipsis)
            break
        maxparts -= 1
        if maxlen < len(part):
            if truncated:
                truncated.append(ellipsis)
            else:
                truncated.append(ellipsis + part[-maxlen:])
            break
        truncated.append(part)
        maxlen -= len(part)
    return ''.join(reversed(truncated))

def _cleanupTraceback(lines, first_line):
    if (not lines) or (len(lines) < 3):
        return u''

    # Remove first line
    del lines[0]

    try:
        clean = []
        index = 0
        indent = " \t"
        while index < len(lines):
            line = lines[index]
            if (0 < index) and not line.startswith(" "):
                # Skip the message at the end (only keep the backtrace)
                break
            line = line.lstrip(indent)

            match = FILE_REGEX.match(line)
            if match is None:
                raise SyntaxError("Unable to parse backtrace")
            filename = truncateFilename(match.group('filename'), 40, 5)
            line_number = match.group('line')

            try:
                source = lines[index + 1].lstrip(indent)
            except IndexError:
                source = None
            if (not source) or FILE_REGEX.match(source):
                # Traceback without source code:
                #    File ".../core.py", line 365, in callService
                #    File ".../component.py", line 31, in __call__
                source = htmlItalic('<%s()>' % match.group('function'))
                index += 1
            else:
                # Traceback with source code:
                #    File ".../core.py", line 365, in callService
                #       return self.function(*args)
                #    File ".../component.py", line 31, in __call__
                index += 2

            where = htmlBold("%s:%s" % (filename, line_number))
            text = Html("%s: %s" % (where, source), escape=False)
            clean.append(text)

        return htmlParagraph(first_line) + htmlList(clean)
    except Exception:
        # Ignore exceptions when cleanup the traceback
        pass
    return htmlParagraph(first_line) + htmlPre(u'\n'.join(lines))

def _getTraceback(err, errtype, traceback):
    # Get server traceback (if any)
    if hasattr(err, "traceback") and err.traceback:
        server = list(err.traceback)
        server = _cleanupTraceback(server, tr("Server backtrace:"))
    else:
        server = u''

    # Get client (local) traceback
    info = None
    if traceback is None:
        try:
            info = sys.exc_info()
            sys.exc_clear()
        except Exception:
            info = None
    else:
        info = (errtype, err, traceback)
    if info:
        client = formatTraceback(info)
        client = _cleanupTraceback(client, tr("Client backtrace:"))
    else:
        client = u''

    return server + client

def formatException(err, debug, traceback=None, errtype=None):
    if errtype is None:
        errtype = type(err)
    if isinstance(err, RpcdError):
        message = unicode(err)
        if debug or (not message):
            message = u"[%s] %s" % (err.type, message)
    else:
        message = exceptionAsUnicode(err, add_type=False)
        if debug or (not message):
            message = u"[%s] %s" % (errtype.__name__, message)
    message = htmlParagraph(message)
    if debug:
        traceback = _getTraceback(err, errtype, traceback)
        if traceback:
            message += traceback
    return unicode(message)

