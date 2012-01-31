#coding: utf-8
"""
Copyright (C) 2009-2011 EdenWall Technologies
Written by Victor Stinner <vstinner AT inl.fr>

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
from logging import Formatter
from twisted.python.failure import Failure
from ufwi_rpcd.common.error import writeError
from ufwi_rpcd.common.logger import LoggerChild, Logger as CommonLogger

class Logger(CommonLogger):
    def __init__(self, *args, **kw):
        CommonLogger.__init__(self, *args, **kw)
        self._with_context = ContextLoggerChild(None, self)

    def debug(self, *arguments):
        self._log(self.logger.debug, arguments)

    def info(self, *arguments):
        self._log(self.logger.info, arguments)

    def warning(self, *arguments):
        self._log(self.logger.warning, arguments)

    def error(self, *arguments):
        self._log(self.logger.error, arguments)

    def critical(self, *arguments):
        self._log(self.logger.critical, arguments)

    def _log(self, func, arguments):
        if len(arguments) == 2:
            context, message = arguments
        else:
            message = arguments[0]
            context = None

        if context and (not context.component):
            message = "%s: %s" % (unicode(context), message)

        extra = {'prefix':self.log_prefix,}

        func(message, extra=extra)

    def writeError(self, *args, **options):
        """
        Display an error with its backtrace. Usage:
          self.writeError(context, err)
        or
          self.writeError(err)
        """
        if not isinstance(args[0], (Failure, Exception)):
            # logger.writeError(context, err, ...): have a context
            context = args[0]
            error = args[1]
            args = args[2:]
        else:
            # logger.writeError(err, ...): no context
            context = None
            error = args[0]
            args = args[1:]
        if isinstance(error, Failure):
            options['traceback'] = error.getBriefTraceback()
            error = error.value
        if context and (not context.component):
            logger = self._with_context
            logger.context = context
            try:
                logger.writeError(error, *args, **options)
            finally:
                logger.context = None
        else:
            CommonLogger.writeError(self, error, *args, **options)

class ContextLoggerChild(LoggerChild):
    def __init__(self, context, logger):
        LoggerChild.__init__(self, logger)
        self.context = context

    def debug(self, message):
        logger = self.getLogger()
        logger.debug(self.context, message)

    def info(self, message):
        logger = self.getLogger()
        logger.info(self.context, message)

    def warning(self, message):
        logger = self.getLogger()
        logger.warning(self.context, message)

    def error(self, message):
        logger = self.getLogger()
        logger.error(self.context, message)

    def critical(self, message):
        logger = self.getLogger()
        logger.critical(self.context, message)

    def writeError(self, error, *args, **options):
        options['logger'] = self
        writeError(error, *args, **options)


