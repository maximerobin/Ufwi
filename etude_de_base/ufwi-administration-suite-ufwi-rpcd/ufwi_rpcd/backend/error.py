"""
Copyright (C) 2007-2011 EdenWall Technologies
Written by Pierre Chifflier <p.chifflier AT inl.fr>

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

import re
from twisted.python.failure import Failure

from ufwi_rpcd.common.transport import TransportError, checkSimpleType
#from ufwi_rpcd.common.tools import deprecationWarning
from ufwi_rpcd.common.tools import toUnicode
from ufwi_rpcd.common.error import (RPCD,
    exceptionAsUnicode as _exceptionAsUnicode)

# Rpcd component error codes
RPCD_CORE = 1
RPCD_SESSION = 2
RPCD_CONFIG = 3
RPCD_AUTH = 4
RPCD_ACL = 5
RPCD_VERSIONNING = 6

# Rpcd.config error codes
CONFIG_ERR_XML_READ = 1
CONFIG_ERR_XML_WRITE = 2
CONFIG_NO_SUCH_KEY = 3
CONFIG_VALUE_DELETED = 4
CONFIG_PATH_TOO_LONG = 5
CONFIG_ALREADY_APPLYING = 6
CONFIG_NO_SUCH_FILE = 7

# Match "%s", not "%% " nor "price: 100%%"
FORMAT_REGEX = re.compile(ur"(?<!%)%[^%]")

TRANSPORT_ERROR_ARGUMENT= '[INTERNAL ERROR]'

class UnicodeException(Exception):
    def __init__(self, *arguments, **keywords):
        if isinstance(arguments[0], (str, unicode)):
            # Old API: raise UnicodeException("error: %s", err)
#            deprecationWarning(
#                "UnicodeException(format, arguments): "
#                "missing application, component and error code",
#                3)
            self.application = 0
            self.component = 0
            self.error_code = 0
            message = arguments[0]
            arguments = arguments[1:]
        else:
            # New API: UnicodeException(app, component, ...)
            self.application = arguments[0]
            self.component = arguments[1]
            if isinstance(arguments[2], (str, unicode)):
                # UnicodeException(app, component, "format", ...): missing code
#                deprecationWarning(
#                    "UnicodeException(application, component, format, arguments): "
#                    "missing error code",
#                    4)
                self.error_code = 0
                message = arguments[2]
                arguments = arguments[3:]
            else:
                # UnicodeException(app, component, errcode, "format", ...): correct
                self.error_code = arguments[2]
                message = arguments[3]
                arguments = arguments[4:]

        self.additionals = []

        # Check arguments / keywords
        if arguments and keywords:
            self.additionals.append(
                u"You can not use arguments *and* keywords with UnicodeException!")
            arguments = None
            keywords = None

        # Convert message to Unicode
        self.unicode_message = toUnicode(message)
        self.format = self.unicode_message

        # Make sure that arguments are serialisable, if no convert them to
        # serialisable type
        if keywords:
            for key, value in keywords.iteritems():
                try:
                    checkSimpleType(value)
                except TransportError, err:
                    keywords[key] = self.formatArgument(value)
                    self.additionals.append(
                        u"The keyword argument %r is unserializable: %s"
                        % (key, err))
        elif arguments:
            arguments = list(arguments)
            for index, value in enumerate(arguments):
                try:
                    checkSimpleType(value)
                except TransportError, err:
                    arguments[index] = self.formatArgument(value)
                    self.additionals.append(
                        u"The argument #%s is unserializable: %s"
                        % (index, err))
            arguments = tuple(arguments)

        # Store arguments
        if keywords:
            self.format_arguments = keywords
        elif arguments:
            self.format_arguments = arguments
        else:
            self.format_arguments = None

        # Check arguments count
        if self.format_arguments:
            count = len(self.format_arguments)
            format_count = len(FORMAT_REGEX.findall(self.format))
            if count < format_count:
                self.additionals.append("Not enough arguments for format string!")
                self.format_arguments = None
            elif format_count < count:
                self.additionals.append("Not all arguments converted during string formatting!")
                self.format_arguments = None

        # Make sure that the format with the arguments
        if self.format_arguments:
            try:
                # check format%args doesn't raise any error
                # text is just used for the readability
                text = self.format % self.format_arguments
            except (UnicodeDecodeError, TypeError), err:
                # Broken arguments: don't format any argument
                self.additionals.append("Format error: don't format any argument! %s" % err)
                self.format_arguments = None

        # Format the message
        if self.format_arguments:
            self.unicode_message = self.unicode_message % self.format_arguments

        # Call parent constructor with the formatted message:
        # use a byte string since Python Exception doesn't support unicode
        bytes_message = unicode(self).encode("ASCII", "replace")
        Exception.__init__(self, bytes_message)

    def getAdditionnals(self):
        if 1 < len(self.additionals):
            return u'\n - '.join(['Additional errors:'] + self.additionals)
        elif 1 == len(self.additionals):
            return u'Additional error: %s' % self.additionals[0]
        else:
            return None

    def __unicode__(self):
        message = self.unicode_message
        additionnals = self.getAdditionnals()
        if additionnals :
            message += u'\n' + additionnals
        return message

    def formatArgument(self, value):
        # Try as unicode characters
        try:
            text = unicode(value)
            checkSimpleType(text)
            return text
        except (UnicodeError, TransportError):
            pass

        # Try as byte string and then reconvert to Unicode
        try:
            text = str(value)
            text = toUnicode(text)
            checkSimpleType(text)
            return text
        except TransportError:
            pass

        # Last chance: replace the value
        return u"[ERROR]"

class RpcdError(UnicodeException):
    pass

class ComponentError(RpcdError):
    pass

class CoreError(ComponentError):
    def __init__(self, *args, **kw):
        ComponentError.__init__(self, RPCD, RPCD_CORE, *args, **kw)

class VersionningError(RpcdError):
    def __init__(self, *args, **kw):
        RpcdError.__init__(self, RPCD, RPCD_VERSIONNING, *args, **kw)

class AclError(RpcdError):
    def __init__(self, *args, **kw):
        RpcdError.__init__(self, RPCD, RPCD_ACL,
            *args, **kw)

class SessionError(RpcdError):
    def __init__(self, *args, **kw):
        RpcdError.__init__(self, RPCD, RPCD_SESSION,
            *args, **kw)

class AuthError(RpcdError):
    def __init__(self, *args, **kw):
        RpcdError.__init__(self, RPCD, RPCD_AUTH,
            *args, **kw)

def exceptionAsUnicode(err, add_type=True):
    if isinstance(err, Failure):
        err = err.value
    if isinstance(err, UnicodeException):
        return unicode(err)
    return _exceptionAsUnicode(err, add_type=add_type)

