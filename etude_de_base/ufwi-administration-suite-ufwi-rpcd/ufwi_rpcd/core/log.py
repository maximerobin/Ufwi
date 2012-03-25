#cofing: utf-8
"""
Copyright (C) 2009-2011 EdenWall Technologies
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
"""

from logging import StreamHandler
from logging.handlers import RotatingFileHandler
from os import umask
import re
from sys import stdout

from twisted.python import log as twisted_python_log

from ufwi_rpcd.backend.logger import Logger
from ufwi_rpcd.common.log_func import getLogLevel, getLogFunc
from ufwi_rpcd.common.logger import createColoredFormatter
from ufwi_rpcd.common.logger import PrefixFormatter

# Text pattern to match an HTTP POST request log line like:
# 127.0.0.1 - - [10/Jul/2009:09:29:42 +0000] "POST /RPC2 HTTP/1.0" 200 1046 "-" "xmlrpclib.py/1.0.1 (by www.pythonware.com)"
# 127.0.0.1 - - [14/Sep/2009:08:39:00 +0000] "POST /RPC2 HTTP/1.1" 200 210 "-" "xmlrpclib.py/1.0.1 (by www.pythonware.com)"
HTTP_POST_PATTERN = re.compile(u'\] "POST /RPC2 HTTP/1\.[01]" ')

# Other possible log entry:
# 221.10.0.114 - - [17/Jul/2009:13:30:47 +0000] "GET /manager/html HTTP/1.1" 404 173 "-" "Mozilla/3.0 (compatible; Indy Library)"

MAX_LOG_FILESIZE = 5 * 1024 * 1024
MAX_LOG_FILES = 10   # including .log, so last file prefix is .log.9

class TwistedLogger:
    """
    Log Twisted errors into nucentral logs
    """
    def __init__(self, print_level):
        self.twisted_logger = Logger("twisted")
        self.stdout_logger = Logger("stdout")
        self.stdout_func = getLogFunc(self.stdout_logger, print_level)

    def log(self, event):
        lines = event['message']
        if event.get('isError'):
            # Twisted error
            logger = self.twisted_logger
            func = self.twisted_logger.error
        elif event.get('printed'):
            if lines and HTTP_POST_PATTERN.search(lines[0]):
                # Ignore HTTP access messages
                return
            logger = self.stdout_logger
            func = self.stdout_func
        else:
            # Other messages
            logger = self.twisted_logger
            func = self.twisted_logger.info
        for line in lines:
            func(line)
        if 'failure' in event:
            failure = event['failure']
            logger.writeError(failure, 'Twisted error')

def setupLog(core):
    # Read the configuration (filename and log levels)
    use_stdout = core.config.getboolean("log", "use_stdout")
    stdout_level = core.conf_get_var_or_default("log", "stdout_level", "ERROR")
    file_level = core.conf_get_var_or_default("log", "file_level", "INFO")
    file_level = getLogLevel(file_level)
    print_level = core.conf_get_var_or_default("log", "print_level", "DEBUG")
    print_level = getLogLevel(print_level)
    filename = core.conf_get_var_or_default("log", "filename", "ufwi-rpcd.log")
    if use_stdout:
        stdout_level = getLogLevel(stdout_level)
        level = min(file_level, stdout_level)
    else:
        level = file_level

    # Get the root logger and remove all existing loggers
    for handler in core.logger.handlers:
        core.logger.removeHandler(handler)
    core.logger.setLevel(level)

    # Create the stdout logger
    if use_stdout:
        handler = StreamHandler(stdout)
        formatter = createColoredFormatter(stdout, display_date=False)
        handler.setFormatter(formatter)
        core.addLogHandler(handler, stdout_level)

    # Create the file logger
    umask(0077)
    handler = RotatingFileHandler(filename, 'a',
        maxBytes=MAX_LOG_FILESIZE, backupCount=(MAX_LOG_FILES - 1),
        encoding='utf8')
    handler.setFormatter(PrefixFormatter(display_date=True))
    core.addLogHandler(handler, file_level)

    # Create a logger for Twisted errors
    core.twisted_logger = TwistedLogger(print_level)
    twisted_python_log.addObserver(core.twisted_logger.log)
