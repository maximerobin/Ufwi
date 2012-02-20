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
from __future__ import with_statement

from os import chmod, fsync
from os.path import basename, join, exists
from shutil import move
from subprocess import PIPE, STDOUT

from error import MAYBE_TEMPORARY_ERROR, NUAUTH_INVALID_CONF, NO_MAPPING_EXISTS
from ufwi_rpcd.backend.process import runCommand
from ufwi_rpcd.common import tr
from ufwi_rpcd.common.process import createProcess, formatCommand
from ufwi_conf.backend.unix_service import runCommandAndCheck, RunCommandError
from .error import NuauthException

_NET_JOIN_SCRIPT = '/usr/share/ufwi_rpcd/scripts/net_join_ad'
_NET_GETLOCALSID = 'net getlocalsid'
_NET_SETLOCALSID = 'net setlocalsid %s'
RUNTIME_FILES_LOCAL_SID = 'local_sid'
RUNTIME_FILES_TDB = 'tdb'

TDBBACKUP_EXE = "/usr/bin/tdbbackup.tdbtools"
TDB_FILES = set(('/var/lib/samba/secrets.tdb',
                 '/var/lib/samba/winbindd_idmap.tdb',))

def joinAd(logger, user, realm, password, block_tcp_53):
    if user is None:
        user = ''
    if realm is None:
        realm = ''
    if password is None:
        password = ''
    if not isinstance(block_tcp_53, basestring):
        raise ValueError("block_tcp_53 must be a string: 'no' or anything")

    #./script admin password DOMAIN_FQDN block_tcp_53(no/other)
    cmd = (_NET_JOIN_SCRIPT, user, password, realm, block_tcp_53)
    cmdstr = formatCommand((_NET_JOIN_SCRIPT, user, '***', realm, block_tcp_53))
    process = createProcess(logger, cmd, stdout=PIPE, stderr=STDOUT, env={}, cmdstr=cmdstr)
    # FIXME: use communicateProcess() with a timeout
    stdout, stderr = process.communicate()
    return_code = process.wait()
    if return_code == 0:
        logger.critical("Join successful to domain %s" % realm)
        return

    stdout = stdout.strip()
    stdout = '\n'.join(stdout.splitlines()[:50])

    if return_code == 1:
        format = tr("Unable to create temp file:\n%s")
    elif return_code == 2:
        format = tr("There was an error while getting a ticket granting ticket:\n%s")
        #Not always critical. continue ? For instance: unreachable server
        raise NuauthException(MAYBE_TEMPORARY_ERROR, format, stdout)
    elif return_code == 4:
        format = tr("There was en error while trying to join the domain:\n%s")
    elif return_code == 10:
        format = tr("Abnormal program termination:\n%s")
    else:
        format = tr("Exit code %s:") % return_code + "\n%s"

    raise NuauthException(NUAUTH_INVALID_CONF, format, stdout)

def check_join(logger, responsible):
    """
    'net ads testjoin' should be sufficient in most cases.
    'net rpc testjoin' is a fallback to 'net ads testjoin'
    """
    responsible.feedback(tr("Checking that the group mappings exist."))
    if not exists("/var/lib/samba/winbindd_idmap.tdb"):
        raise NuauthException(NO_MAPPING_EXISTS, "The group mappings don't exist")
    try:
        cmd = ('/usr/bin/net', 'ads', 'testjoin')
        runCommandAndCheck(logger, cmd)
    except RunCommandError:
        pass # another test
    else:
        responsible.feedback(tr("The junction to the Active Directory domain is functional"))
        return # ok

    try:
        cmd = ('/usr/bin/net', 'rpc', 'testjoin')
        runCommandAndCheck(logger, cmd)
    except RunCommandError:
        if responsible is not None:
            responsible.feedback(
                tr("No junction to an Active Directory domain.")
            )
        raise NuauthException(NUAUTH_INVALID_CONF,
            "Domain not available")
    responsible.feedback(tr("The junction to the Active Directory domain is functional"))

def getLocalSidPath(var_path):
    return join(var_path, 'ufwi_conf', 'nuauth_localsid')

def getBackupPath(var_path):
    return join(var_path, 'ufwi_conf')

def saveLocalSid(component):
    """save local sid (default in /var/lib/ufwi_rpcd/ufwi_conf/nuauth_localsid)"""
    proc = createProcess(component, _NET_GETLOCALSID.split(), stdout=PIPE, locale=False)
    outputs = proc.communicate()
    stdout = outputs[0]
    retcode = proc.wait()
    if retcode != 0 or not stdout:
        component.critical("Can not fetch 'localsid'."
            " 'localsid' will not be exported. SSO with high availability will fail")
        # TODO raise an error which will be non blocking if we are not in HA ?
        return

    vardir = component.core.config.get('CORE', 'vardir')
    output_path = getLocalSidPath(vardir)

    # output sample of net getlocalsid:
    # SID for domain EW4-TEST1 is: S-1-5-21-4286993159-1593211551-402818373
    line = stdout.splitlines()[0]
    sid = line.split()[-1] # last element
    with open(output_path, 'w') as output_file:
        output_file.flush()
        fsync(output_file.fileno())
        output_file.write(sid)

    msg = "netlocalsid is '%s' and was saved in '%s'"
    component.info(msg % (sid, output_path))

def configureLocalSid(component):
    var_dir = component.core.config.get('CORE', 'vardir')
    sid_path = getLocalSidPath(var_dir)
    with open(sid_path) as sid_file:
        content = sid_file.readlines()
    if content:
        sid = content[0]
    else:
        return False

    cmd = _NET_SETLOCALSID % sid
    cmd = cmd.split()
    proc = createProcess(component, cmd, stdout=PIPE, stderr=STDOUT, locale=False)
    outputs = proc.communicate() # stdout, stderr
    retcode = proc.wait()
    if retcode != 0:
        stdout = outputs[0]
        msg = "can not save local SID '%s', error: '%s'"
        component.critical(msg % (sid, stdout))
        return False
    else:
        component.info("successfully set local SID '%s'" % sid)

    return True

_SAMBA_FILES_PREFIX = "[tdb-sid]"
def _samba_info(component, message):
    """Use provided component log facility, add a prefix"""
    component.info("%s %s" % (_SAMBA_FILES_PREFIX, message))

def _del_runtimefile(component, files, deleted_file):
    """Mark a file for deletion"""
    _samba_info(component, "Marking for deletion by archive: '%s'" % deleted_file)
    #files['deleted'] is a tuple of files
    files['deleted'] = files['deleted'] + (deleted_file,)

def _add_runtimefile(component, files, added_file, description):
    """Append a file in files to be packaged"""
    _samba_info(component, "Adding in archive: '%s' (%s)" % (added_file, description))
    #files['added'] is a list of duples
    files['added'] += ((added_file, description),)

def sambaRuntimeFiles(component, files):
    """backup samba files and add them to runtimefiles"""
    _samba_info(component, "Backuping Active Directory Data")
    var_dir = component.core.config.get('CORE', 'vardir')
    sid_bckp = getLocalSidPath(var_dir)
    tdb_path = getBackupPath(var_dir)

    # before 37: never created
    # after 37: created during join
    # code needed when updating from 36 to 37, keep it just in case
    if not exists(sid_bckp):
        component.info("save missing local SID")
        saveLocalSid(component)

    delete = []
    added_files = []
    delete.append(sid_bckp)
    added_files.append((sid_bckp, RUNTIME_FILES_LOCAL_SID))

    for tdb_file in TDB_FILES:
        delete.append(tdb_file)
        cmd = [TDBBACKUP_EXE, tdb_file]
        runCommand(component, cmd, timeout=120)
        tdb_file_bckp = '%s.bak' % tdb_file

        _samba_info(component, "move %s -> %s" % (tdb_file_bckp, tdb_path))
        move(tdb_file_bckp, tdb_path)

        added_files.append(
            (join(tdb_path, basename(tdb_file_bckp)),
            RUNTIME_FILES_TDB)
            )

    for filename in delete:
        _del_runtimefile(component, files, filename)
    for filename, description in added_files:
        _add_runtimefile(component, files, filename, description)

def sambaRuntimeFilesModified(component):
    """restore tdb files"""
    _samba_info(component, "Restoring Active Directory Data")
    var_dir = component.core.config.get('CORE', 'vardir')
    tdb_path = getBackupPath(var_dir)

    for tdb_file in TDB_FILES:
        tdb_bckp = tdb_file
        tdb_bckp = basename(tdb_bckp)
        tdb_bckp = join(tdb_path, tdb_bckp)
        # this command check if tdb file is ok (trying to restore if corrupt)
        cmd = [TDBBACKUP_EXE, '-v', tdb_bckp]
        runCommand(component, cmd, timeout=120)
        _samba_info(component, "move %s -> %s" % (tdb_bckp, '/var/lib/samba'))
        move(tdb_bckp, '/var/lib/samba')
        chmod(tdb_path, 0600)
        component.chownWithNames(tdb_path, 'root', 'root')

