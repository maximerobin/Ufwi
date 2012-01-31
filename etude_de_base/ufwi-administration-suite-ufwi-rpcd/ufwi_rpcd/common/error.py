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

from logging import getLogger, ERROR, DEBUG
from sys import exc_info, exc_clear, hexversion
from traceback import format_exception
from ufwi_rpcd.common.log_func import getLogFunc
from ufwi_rpcd.common.tools import toUnicode
from socket import error as socket_error

# Application error codes (0 means "unknown")
RPCD = 12
NUCONF = 13
RULESET = 14
NULOG = 15
NUPKI = 16
NURESTORE=17
NUDPI=18

RPCD_ERRORS = Exception

class UnicodeException(Exception):
    def __init__(self, message):
        self.unicode_message = toUnicode(message)
        bytes_message = self.unicode_message.encode("ASCII", "replace")
        Exception.__init__(self, bytes_message)

    def __unicode__(self):
        return self.unicode_message

def formatTraceback(traceback):
    if not isinstance(traceback, str):
        traceback = format_exception(*traceback)
        if traceback == ["None\n"]:
            return None

        traceback = ''.join(traceback)
    traceback = traceback.rstrip()
    lines = traceback.splitlines()
    return [toUnicode(line) for line in lines]

def writeBacktrace(logger, log_level=ERROR, clear=True,
traceback=None, prefix=''):
    log_func = getLogFunc(logger, log_level)
    try:
        if not traceback:
            traceback = exc_info()
            if clear:
                exc_clear()
        traceback = formatTraceback(traceback)
        if traceback:
            for line in traceback:
                log_func(prefix + line.rstrip())
            return
        err = "empty traceback"
    except Exception, err:
        pass
    log_func("Unable to get backtrace: %s" % err)

def exceptionAsUnicode(err, add_type=True):
    r"""
    add_type option changes the output for KeyError and exception with an empty
    message (eg. AssertionError). If the option is True (default): add the type
    as prefix, otherwise return an empty string.

    >>> exceptionAsUnicode(Exception("ascii"))
    u'ascii'
    >>> exceptionAsUnicode(Exception("h\xe9 h\xe9"))
    u'h\xe9 h\xe9'
    >>> exceptionAsUnicode(UnicodeException(u"h\xe9 h\xe9"))
    u'h\xe9 h\xe9'
    >>> exceptionAsUnicode(AssertionError())
    u'[AssertionError]'
    >>> exceptionAsUnicode(KeyError(3))
    u'[KeyError] 3'
    >>> exceptionAsUnicode(KeyError(3), False)
    u'3'
    """
    if isinstance(err, (IOError, OSError)) and err.strerror:
        # Get "message" instead of "(42, 'message')"
        return toUnicode(err.strerror)
    if isinstance(err, socket_error):
        # Get 'Connexion refus\xc3\xa9e' instead of
        # (111, 'Connexion refus\xc3\xa9e')
        args = err.args
        if 2 <= len(args):
            msg = args[1]
        else:
            msg = args[0]
        return toUnicode(msg)
    try:
        text = unicode(err)
    except (UnicodeDecodeError, UnicodeEncodeError):
        as_bytes = str(err)
        text = toUnicode(as_bytes)
    if add_type:
        if isinstance(err, KeyError):
            # KeyError message is the key, which is usually meaningless:
            # add [KeyError] prefix
            text = u"[%s] %s" % (err.__class__.__name__, text)
        elif not text:
            # Some errors (eg. AssertionError) have no text, so display the
            # exception type instead of an empty string
            text = u"[%s]" % err.__class__.__name__
    return text

def formatError(error):
    r"""
    Format an error with its type as prefix.

    >>> formatError(UnicodeException(u"h\xe9 h\xe9"))
    u'[UnicodeException] h\xe9 h\xe9'
    >>> formatError(KeyError(3))
    u'[KeyError] 3'
    >>> formatError(AssertionError())
    u'[AssertionError]'
    """
    err_type = error.__class__.__name__
    message = exceptionAsUnicode(error, False)
    if message:
        return u"[%s] %s" % (err_type, message)
    else:
        return u"[%s]" % (err_type,)

def writeError(error, title=u"ERROR", log_level=ERROR, logger=None,
message=None, traceback=None, traceback_level=DEBUG):
    if not logger:
        logger = getLogger()
    if hexversion < 0x02050000 \
    and error.__class__ in (SystemExit, KeyboardInterrupt):
        # Ignore sys.exit() and CTRL+c in:
        # try/except Exception, err: writeError(err, ...)
        # (only needed for Python 2.4)
        raise error
    log_func = getLogFunc(logger, log_level)
    if not message:
        message = formatError(error)
    log_func(u"%s: %s" % (title, message))
    clear = bool(traceback)
    writeBacktrace(logger, log_level=traceback_level,
        clear=clear, traceback=traceback, prefix='| ')

def reraise(new_err):
    """
    Raise an exception but keep current traceback.

    Example: ::

       try:
          ...
       except:
          reraise(MyError("..."))

    MyError will be raised with the original traceback.
    """
    err_cls, err, traceback = exc_info()
    raise new_err.__class__, new_err, traceback

