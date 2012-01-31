"""
Copyright (C) 2008-2011 EdenWall Technologies
Written by Victor Stinner <victor.stinner AT inl.fr>

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

$Id$
"""

import locale
import sys

def getTerminalCharset():
    """
    Guess terminal charset using differents tests:
    1. Try locale.getpreferredencoding()
    2. Try locale.nl_langinfo(CODESET)
    3. Try sys.stdout.encoding
    4. Otherwise, returns "ASCII"

    WARNING: Call locale.setlocale(locale.LC_ALL, "") before calling this function.
    """
    # (1) Try locale.getpreferredencoding()
    try:
        charset = locale.getpreferredencoding()
        if charset:
            return charset
    except (locale.Error, AttributeError):
        pass

    # (2) Try locale.nl_langinfo(CODESET)
    try:
        charset = locale.nl_langinfo(locale.CODESET)
        if charset:
            return charset
    except (locale.Error, AttributeError):
        pass

    # (3) Try sys.stdout.encoding
    if hasattr(sys.stdout, "encoding") and sys.stdout.encoding:
        return sys.stdout.encoding

    # (4) Otherwise, returns "ASCII"
    return "ASCII"

class UnicodeStdout:
    def __init__(self, device, charset):
        self.device = device
        self.charset = charset

    def flush(self):
        self.device.flush()

    def write(self, text):
        if isinstance(text, unicode):
            text = text.encode(self.charset, 'replace')
        self.device.write(text)

    def isatty(self):
        if hasattr(self.device, "isatty"):
            return self.device.isatty()
        else:
            return False

def installUnicodeStdout():
    if 'readline' in sys.modules:
        # UnicodeStdout conflicts with the readline module
        return
    if installUnicodeStdout.done:
        return
    installUnicodeStdout.done = True
    # Setup locales
    try:
        locale.setlocale(locale.LC_ALL, "")
    except (locale.Error, IOError):
        pass

    # Setup Unicode stdout
    charset = getTerminalCharset()
    sys.stdout = UnicodeStdout(sys.stdout, charset)
    sys.stderr = UnicodeStdout(sys.stderr, charset)
    return charset
installUnicodeStdout.done = False

def uninstallUnicodeStdout():
    if isinstance(sys.stdout, UnicodeStdout):
        sys.stdout = sys.stdout.device
    if isinstance(sys.stderr, UnicodeStdout):
        sys.stderr = sys.stderr.device

