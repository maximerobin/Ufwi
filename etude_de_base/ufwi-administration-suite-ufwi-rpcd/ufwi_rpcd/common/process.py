
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

from __future__ import with_statement
import os
from os import listdir
from os.path import devnull, join as joinpath
from time import sleep
from subprocess import Popen
from select import select

import platform
if platform.system() != 'Windows':
    from fcntl import fcntl, F_GETFL, F_SETFL
    from os import kill, O_NONBLOCK
    from signal import SIGINT, SIGKILL

from ufwi_rpcd.common.error import UnicodeException, exceptionAsUnicode
from ufwi_rpcd.common.tools import toUnicode

# Use monotonic_time() to ignore NTP time update
from ufwi_rpcd.common.monotonic_time import monotonic_time

LOCALE_ENVVARS = (
    'LC_ALL', 'LANG', 'LANGUAGE',
    'LC_CTYPE', 'LC_NUMERIC', 'LC_TIME', 'LC_COLLATE', 'LC_MONETARY',
    'LC_MESSAGES', 'LC_PAPER', 'LC_NAME', 'LC_ADDRESS', 'LC_TELEPHONE',
    'LC_MEASUREMENT', 'LC_IDENTIFICATION')

class ProcessError(UnicodeException):
    pass

def escape(value):
    r"""
    Simple examples:

    >>> print escape('a')
    a
    >>> print escape('a b')
    'a b'
    >>> print escape(r"a\b")
    'a\b'
    >>> print escape('a"b')
    'a"b'

    The '!' character have to be written between apostrophes:

    >>> print escape("a!")
    'a!'
    >>> print escape("a!b'c")
    'a!b'"'"'c'

    Write an apostrophe between quotes:

    >>> print escape("a'b")
    "a'b"
    >>> print escape(r"a'b\c")
    "a'b\\c"
    """
    apos = "'"  # '
    quot = '"'  # "
    value = unicode(value)
    if any((char in "\\ \"';|!*?") for char in value):
        if (apos not in value) or ('!' in value):
            value = value.replace(apos, "'\"'\"'")
            value = apos + value + apos
        else:
            value = value.replace('\\', r'\\')
            value = value.replace(quot, r'\"')
            value = quot + value + quot
    return value

def formatCommand(command):
    if isinstance(command, (list, tuple)):
        return u' '.join(escape(arg) for arg in command)
    else:
        return unicode(command)

def createProcess(logger, command, **popen_args):
    """
    Create a process using subprocess.Popen(command, **popen_args):
     - if stdin is not set, use /dev/null
     - if close_fds is not set, use close_fds=True (except on Windows)

    If you need to hide the command in the logs, use the cmdstr argument (eg.
    cmdstr='command login ***').

    To disable locale (remove LC_ALL, LANG, ... environment variables), use
    locale=False option.

    Return the process object.
    """
    if 'cmdstr' not in popen_args:
        cmdstr = formatCommand(command)
    else:
        cmdstr = popen_args.pop('cmdstr')

    # Remove locale variables?
    try:
        locale = popen_args.pop('locale')
    except KeyError:
        locale = True
    if not locale:
        if 'env' not in popen_args:
            popen_args['env'] = dict(os.environ)
        env = popen_args['env']
        for key in LOCALE_ENVVARS:
            if key not in env:
                continue
            del env[key]

    # Set default options
    if 'close_fds' not in popen_args:
        popen_args['close_fds'] = True
    if 'stdin' not in popen_args:
        stdin_file = open(devnull, 'rb')
        popen_args['stdin'] = stdin_file
    else:
        stdin_file = None

    if platform.system() == 'Windows':
        # Raises NotImplementedError() on Windows
        popen_args.pop('close_fds')
        popen_args.pop('stdin')


    try:
        message = "Execute command: %s" % cmdstr
        try:
            process = Popen(command, **popen_args)
        except Exception, err:
            errmsg = exceptionAsUnicode(err)
            logger.debug("%s -> error" % message)
            raise ProcessError(u'createProcess("%s") error: %s' % (cmdstr, errmsg))
        message = "%s -> process %s" % (message, process.pid)
        logger.debug(message)

        return process
    finally:
        if stdin_file:
            stdin_file.close()

def terminateProcess(logger, process):
    """
    Terminate the process using SIGINT and SIGKILL. Return the exit status
    (result of process.poll()).

    Send a ProcessError if the process is still running after 15 seconds.
    """
    if platform.system() == 'Windows':
        raise NotImplementedError()
    # Send a first SIGINT signal
    pid = process.pid
    logger.warning("Send SIGINT to process %s" % pid)
    kill(pid, SIGINT)
    sigint = 1

    # Loop to wait process exit
    start = monotonic_time()
    timeout = 15.0           # Give 15 seconds to the process to exit
    next_msg = start + 1.5   # Print first message after 1.5 seconds
    while True:
        # Timeout?
        since = monotonic_time() - start
        if timeout < since:
            raise ProcessError("Unable to kill process %s after %.1f seconds" % (
                pid, since))

        # Inform user about this loop
        if next_msg <= monotonic_time():
            # Print the message at 1.5 seconds, 5.5 seconds, 10.5 seconds, ...
            next_msg = monotonic_time() + 5.0
            logger.warning("Wait process %s death (since %.1f seconds)..."
                % (pid, since))

        # Is process terminated?
        status = process.poll()
        if status is not None:
            return status

        if since < 0.5:
            # 0..500 ms: read the status each 100 ms
            sleep(0.100)
        elif since < 1.0:
            if sigint < 2:
                # send INT signal at 500 ms
                logger.warning("Send SIGINT to process %s" % pid)
                kill(pid, SIGINT)
                sigint += 1
            # 500..1000 ms: read the status each 250 ms
            sleep(0.250)
        else:
            # After one second: send KILL signal and read the status each 500 ms
            logger.warning("Send SIGKILL to process %s" % pid)
            kill(pid, SIGKILL)
            sleep(0.500)

def _file_setblocking(fd, blocking):
    flags = fcntl(fd, F_GETFL)
    if blocking:
        flags |= O_NONBLOCK
    else:
        flags &= ~O_NONBLOCK
    fcntl(fd, F_SETFL, flags)

def _waitProcess(logger, process, timeout, read_pipes):
    if platform.system() == 'Windows':
        raise NotImplementedError()
    pid = process.pid
    start = monotonic_time()
    pause = 0.025

    # Setup pipes
    stdout = None
    stderr = None
    chunk_size = 4096
    if read_pipes:
        pipes_fd = []
        if process.stdout is not None:
            stdout_fd = process.stdout.fileno()
            _file_setblocking(stdout_fd, False)
            pipes_fd.append(stdout_fd)
            stdout = []
        else:
            stdout_fd = None
        if process.stderr is not None:
            stderr_fd = process.stderr.fileno()
            _file_setblocking(stderr_fd, False)
            pipes_fd.append(stderr_fd)
            stderr = []
        else:
            stderr_fd = None
        if pipes_fd:
            def decodeOutput(chunks):
                return [
                    toUnicode(line)
                    for line in ''.join(chunks).splitlines()]
        else:
            read_pipes = False

    while True:
        # Execution timeout?
        since = monotonic_time() - start
        if timeout < since:
            break

        # Read pipes
        if read_pipes:
            while 1:
                read, write, err = select(pipes_fd, (), (), 0)
                if not read:
                    break
                done = False
                if stdout_fd in read:
                    chunk = os.read(stdout_fd, chunk_size)
                    stdout.append(chunk)
                    if not chunk:
                        done = True
                if stderr_fd in read:
                    chunk = os.read(stderr_fd, chunk_size)
                    stderr.append(chunk)
                    if not chunk:
                        done = True
                if done:
                    break

        # Read process status
        status = process.poll()
        if status is not None:
            # Process exit: done
            message = "Process %s exited: status=%s" % (process.pid, status)
            if status != 0:
                logger.warning(message)
            else:
                logger.debug(message)
            if stdout is not None:
                stdout = decodeOutput(stdout)
            if stderr is not None:
                stderr = decodeOutput(stderr)
            return status, stdout, stderr

        # Sleep few milliseconds
        if 5.0 <= since:
            pause = 0.500
        elif 1.0 <= since:
            pause = 0.250
        elif 0.250 <= since:
            pause = 0.100
        sleep(pause)

    # Terminate the process and wait its death
    terminateProcess(logger, process)

    # Raise an error (execution timeout)
    raise ProcessError("Abort process %s: timeout (%.1f sec)!" % (pid, since))

def waitProcess(logger, process, timeout):
    """
    Wait for process exit. Return process exit status (result of
    process.poll()).

    If the process is still running after 'timeout' seconds: terminate the
    process using terminateProcess() and raise a ProcessError.

    Use communicateProcess() if stdout or stderr is redirected to a pipe.
    """
    status, stdout, stderr = _waitProcess(logger, process, timeout, False)
    return status

def communicateProcess(logger, process, timeout):
    """
    Wait for process exit and read its pipes. Return (status, stdout, stderr):

     - status is the process exit status (result of process.poll())
     - stdout is a list of unicode strings (if stdout is a PIPE) or None
     - stderr is a list of unicode strings (if stdout is a PIPE) or None

    If the process is still running after 'timeout' seconds: terminate the
    process using terminateProcess() and raise a ProcessError.
    """
    return _waitProcess(logger, process, timeout, True)

def readProcessOutput(stdout, max_nb_lines):
    """
    max_nb_lines: magic value for all the lines is -1 for instance
    """
    if platform.system() == 'Windows':
        raise NotImplementedError()
    # Get the process output
    lines = []
    for nlines, line in enumerate(stdout):
        if nlines == max_nb_lines:
            lines.append("... (more than %s lines)" % max_nb_lines)
            break
        line = line.rstrip()
        line = toUnicode(line)
        lines.append(line)
    return lines

_PROC = "/proc"
_STAT = "stat"

def getProcessName(pid, is_string = False):
    if platform.system() == 'Windows':
        raise NotImplementedError()
    if not is_string:
        pid = unicode(pid)
    with open(joinpath(_PROC, pid, _STAT)) as fd:
# stat looks like this:
# 14543 (squidGuard) Z 14541 14541 14541 0 -1 4194316 3832 0 0 0 2 4 0 0 20 0 1 0 23910082 0 0 4294967295 0 0 0 0 0 0 0 4096 0 0 0 0 17 0 0 0 0 0 0
        exe_name = fd.read().split(" ")[1].strip("()")
        return exe_name

def getProcesses():
    if platform.system() == 'Windows':
        raise NotImplementedError()
    proc_fnames = listdir(_PROC)
    for fname in proc_fnames:
        try:
            pid = int(fname)
        except ValueError:
            #not a process directory (ValueError)
            pass
        else:
            #a process directory (can be read as int)
            try:
                exe_name = getProcessName(fname, is_string = True)
            except Exception:
                #not found etc
                continue
            #'' named processes are not relevant to us
            if exe_name:
                yield (pid, exe_name)

def getPidByName(name):
    """
    Generator
    Tries and get the pids for an exe name supplied
    Do not enter full path:
        Input "apache2", not "/usr/sbin/apache2"
    """
    if platform.system() == 'Windows':
        raise NotImplementedError()
    for (pid, exe_name) in getProcesses():
        if name == exe_name:
            yield pid

