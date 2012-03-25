#coding: utf-8
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
import weakref
from sys import platform
from logging import getLogger
from logging import Formatter
from logging import StreamHandler
from logging import ERROR

from ufwi_rpcd.common.error import writeError

RESET_SEQ = "\033[0m"
COLOR_SEQ = "%s%%s" + RESET_SEQ

IMPORTANT_LEVEL = ERROR + 1
IMPORTANT = 'Level %d' % IMPORTANT_LEVEL

COLORS = {
    'DEBUG': COLOR_SEQ % "\033[36m",
    'INFO': "%s",
    'WARNING': COLOR_SEQ % "\033[1;1m",
    'ERROR': COLOR_SEQ % "\033[1;31m",
    'CRITICAL': COLOR_SEQ % ("\033[1;33m\033[1;41m"),
    IMPORTANT: COLOR_SEQ % ("\033[1;1m"),
}

class Logger(object):
    """
    A logger has methods debug(msg), info(msg), warning(msg), error(msg).

    Constructor: ::

       Logger.__init__("ufwi_ruleset")
       -> prefix '[ufwi_ruleset] '
       Logger.__init__("ufwi_ruleset", "iptables")
       -> prefix '[ufwi_ruleset][iptables] '
       Logger.__init__("module_loader", parent=core)
       -> prefix '[core][module_loader] '
       Logger.__init__("config", domain="config.apply")
       -> prefix '[config] '
    """
    def __init__(self, *prefixes, **options):
        prefix = '.'.join(prefixes)
        domain = options.get('domain', None)
        parent = options.get('parent')
        if parent:
            prefix = "%s.%s" % (parent.log_prefix, prefix)
        if prefix:
            self.log_prefix = prefix
        else:
            self.log_prefix = ''
        self.logger = getLogger(domain)

    def addLogHandler(self, handler, level):
        handler.setLevel(level)
        self.logger.addHandler(handler)
        return handler

    def addLogStreamHandler(self, stream, level, format='%(prefix)s %(message)s'):
        handler = StreamHandler(stream)
        handler.setFormatter(Formatter(format))
        return self.addLogHandler(handler, level)

    def removeHandler(self, handler):
        self.logger.removeHandler(handler)

    def debug(self, message):
        self._log(self.logger.debug, message)

    def info(self, message):
        self._log(self.logger.info, message)

    def warning(self, message):
        self._log(self.logger.warning, message)

    def error(self, message):
        self._log(self.logger.error, message)

    def critical(self, message):
        self._log(self.logger.critical, message)

    def _log(self, func, message):
        message = message
        extra = {'prefix':self.log_prefix}
        func(message, extra=extra)

    def important(self, message):
        extra = {'prefix':self.log_prefix}
        self.logger.log(ERROR + 1, message, extra=extra)

    def writeError(self, error, *args, **options):
        options['logger'] = self
        writeError(error, *args, **options)

class LoggerChild(object):
    """
    Delegate logging functions to another logger.
    Parent logger have to be a Logger class (methods
    debug()..critical(), writeError()).
    """
    def __init__(self, logger):
        self._logger = weakref.ref(logger)

    def debug(self, message):
        logger = self.getLogger()
        logger.debug(message)

    def info(self, message):
        logger = self.getLogger()
        logger.info(message)

    def warning(self, message):
        logger = self.getLogger()
        logger.warning(message)

    def error(self, message):
        logger = self.getLogger()
        logger.error(message)

    def critical(self, message):
        logger = self.getLogger()
        logger.critical(message)

    def getLogger(self):
        logger = self._logger()
        if not logger:
            raise ValueError("Broken reference to the logger")
        return logger

    def writeError(self, error, *args, **options):
        logger = self.getLogger()
        logger.writeError(error, *args, **options)

class PrefixFormatter(Formatter):
    """formatter which use prefix if available"""

    PREFIX_FMT = '[%(prefix)s] %(message)s'
    SIMPLE_FMT = '%(message)s'

    def __init__(self, display_date=True, datefmt=None):
        Formatter.__init__(self, datefmt=datefmt)
        self.display_date = display_date

    def format(self, record):
        # Follow Formatter.format(...)
        record.message = record.getMessage()

        if not hasattr(record, 'prefix'):
            s = PrefixFormatter.SIMPLE_FMT % record.__dict__
        else:
            s = PrefixFormatter.PREFIX_FMT % record.__dict__

        if self.display_date:
            record.asctime = self.formatTime(record, self.datefmt)
            s = record.asctime + ': ' + s

        if record.exc_info:
            # Cache the traceback text to avoid converting it multiple times
            # (it's constant anyway)
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            if s[-1:] != "\n":
                s = s + "\n"
            s = s + record.exc_text
        return s

class ColoredFormatter(PrefixFormatter):
    """
    Class written by airmind:
    http://stackoverflow.com/questions/384076/how-can-i-make-the-python-logging-output-to-be-colored
    """
    def format(self, record):
        levelname = record.levelname
        msg = PrefixFormatter.format(self, record)
        if levelname in COLORS:
            msg = COLORS[levelname] % msg
        else:
            print "*" * 100, levelname, "(%s)" % type(levelname), "not in", COLORS.keys()
        return msg

def createColoredFormatter(stream, display_date=True, datefmt=None):
    if (platform != 'win32') and stream.isatty():
        return ColoredFormatter(display_date=display_date, datefmt=datefmt)
    else:
        return Formatter('%(message)s')

