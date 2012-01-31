
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

from os import getuid, symlink, unlink
from os.path import exists

from ufwi_rpcd.common.process import createProcess, waitProcess

SUDO_PROGRAM = ('/usr/bin/sudo', '-S')
RPCD_SUDO_PROGRAM = '/usr/sbin/ufwi_rpcd_sudo'
DEFAULT_TIMEOUT = 5 * 60

def runCommand(logger, command, timeout=DEFAULT_TIMEOUT, **popen_args):
    """
    use only if stdin/stdout/stderr are NOT pipes (instead use createProcess
    and communicateProcess)
    """
    process = createProcess(logger, command, **popen_args)
    status = waitProcess(logger, process, timeout)
    return (process, status)

def runCommandAsRoot(logger, command, timeout=DEFAULT_TIMEOUT, stdin_filename=None, **popen_args):
    """
    Run the specified command as root using sudo and wait until it exits.

    Options:
     - timeout: stop the process if it runs more than 'timeout' seconds
     - stdin_filename: open the specified file as stdin file
     - any Popen keyword, eg. stdout=subprocess.PIPE

    If timeout of stdin_filename is used, use ufwi_rpcd_sudo program.

    Return the tuple (process, exit_status):
     - process: the subprocess.Popen() object
     - exit_status: exit status, result of process.poll()
    """
    assert isinstance(command, (list, tuple))
    stdin_file = None
    if getuid() != 0:
        arguments = list(SUDO_PROGRAM)
        if timeout or stdin_filename:
            # ufwi-rpcd is not running as root, ufwi_rpcd_sudo is required to
            # send a signal (SIGTERM, SIGKILL) to the child process (to kill it
            # after the timeout) which is running as root
            arguments += [RPCD_SUDO_PROGRAM]
            if timeout:
                arguments.append('--timeout=%s' % timeout)
            if stdin_filename:
                arguments.append('--stdin=%s' % stdin_filename)
            arguments.append('--')
    else:
        arguments = []
        if stdin_filename:
            stdin_file = open(stdin_filename, 'rb')
            popen_args['stdin'] = stdin_file
    arguments.extend(command)
    process, status = runCommand(logger, arguments, timeout=timeout, **popen_args)
    if stdin_file:
        stdin_file.close()
    return (process, status)

def is_enabled_in_runit(service):
    """
    Return True if the service is enabled in runit.
    """
    return exists('/etc/service/%s' % service)

def set_enabled_in_runit(logger, enable, service):
    """
    - If enable is True: return True if the symlink has been created, False if it
      does already exist
    - If enable is False: return True if the symlink has been deleted, False if
      it didn't existed
    """
    if enable:
        text = "Enable %s service in runit: " % service
        result = (not is_enabled_in_runit(service))
        if result:
            symlink('/etc/sv/%s' % service, '/etc/service/%s' %  service)
            text += "symlink created"
        else:
            text += "(symlink already exists)"
    else:
        text = "Disable %s service in runit: " % service
        result = is_enabled_in_runit(service)
        if result:
            unlink('/etc/service/%s' % service)
            text += "symlink deleted"
        else:
            text += "(symlink doesn't exist)"
    logger.info(text)
    return result

