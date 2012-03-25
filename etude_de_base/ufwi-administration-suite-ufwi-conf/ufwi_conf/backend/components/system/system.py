# -*- coding: utf-8 -*-

"""
Copyright (C) 2008-2011 EdenWall Technologies
Written by Michael Scherer <m.scherer AT inl.fr>

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

from __future__ import with_statement

from os.path import exists
import codecs
import subprocess

from twisted.internet.threads import deferToThread

from ufwi_rpcd.common import tr
from ufwi_rpcd.common.tools import toUnicode
from ufwi_rpcd.common.getter import getBoolean
from ufwi_rpcd.common.process import createProcess, communicateProcess
from ufwi_rpcd.backend import Component, ComponentError
from ufwi_rpcd.backend.variables_store import VariablesStore
from ufwi_conf.backend.nnd_instance import getclient

USER_GROUPS_FILENAME = '/var/cache/ufwi_rpcd/groups'

STORAGE_FILENAME = "/var/lib/ufwi_rpcd/ufwi_conf/system.xml"

class SystemException(ComponentError):
    pass

class SystemComponent(Component):
    NAME = "system"
    VERSION = "1.0"
    API_VERSION = 2

    ROLES = {
        'conf_read': set((
            'getUserGroups', 'getAllGroups', 'status',
        )),
    }

    def init(self, core):
        self.use_nnd = False
        self.nnd_client = None
        if exists(STORAGE_FILENAME):
            storage = VariablesStore()
            storage.load(STORAGE_FILENAME)
            try:
                use_nnd = storage['use_nnd']
            except KeyError:
                pass
            else:
                self._setUseNND(use_nnd)

    def destroy(self):
        if self.nnd_client:
            self.nnd_client.quit()

    def _parseGetent(self):
        groups = set()
        process = createProcess(self,
            ['/usr/bin/getent', 'group'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        # read output with a timeout of 5 minutes
        status, stdout, stderr = communicateProcess(self, process, 60.0*5)
        if status:
            logs = stdout[20:] + stderr[20:]
            raise ComponentError(tr("getent command failed:\n%s"), logs)
        for line in stdout:
            parts = line.split(u':')
            name = parts[0]
            gid = int(parts[2])
            groups.add((name, gid))
        return groups

    def _parseGroup(self):
        groups = set()
        with open('/etc/group') as fp:
            for line in fp.readlines():
                line = line.rstrip()
                name = line.split(':')[0]
                name = toUnicode(name)
                groups.add(name)
        return groups

    def _getGroups(self, only_user_groups):
        groups = []
        if self.use_nnd:
            if self.nnd_client is None:
                self.nnd_client = getclient(self)
            groups = [
                (groupname, "")
                for groupname in self.nnd_client.searchgroups()
                ]
        else:
            system_group_names = self._parseGroup()
            getent = self._parseGetent()
            for entry in getent:
                if only_user_groups and (entry[0] in system_group_names):
                    continue
                groups.append(entry)
        groups.sort()
        return groups

    def _exportGroups(self, groups):
        # Convert group number to string to avoid the XML-RPC limit (2^31-1)
        return tuple((name, str(number)) for name, number in groups)

    def _getUserGroups(self, use_cache=True):
        group_list = []
        if (not use_cache) or (not exists(USER_GROUPS_FILENAME)):
            with codecs.open(USER_GROUPS_FILENAME, 'w', encoding='utf8') as fp:
                groups = self._getGroups(True)
                for entry in groups:
                    group_list.append(entry)
                    fp.write(u'%s:%s\n' % (entry[0], entry[1]))
        else:
            with codecs.open(USER_GROUPS_FILENAME, 'r', encoding='utf8') as fp:
                for line in fp:
                    line = line.rstrip()
                    entry = line.rsplit(':', 1)
                    group_list.append(entry)
        return self._exportGroups(group_list)

    # Use a default value for use_cache=False to keep the backward compatibilty
    def service_getUserGroups(self, context, use_cache=True):
        """
        Get user groups as list of (name, gid): (unicode, str).

        If the cache doesn't exist, it will be created at the first call, even
        if use_cache is False.
        """
        return deferToThread(self._getUserGroups, use_cache)

    def _getAllGroups(self):
        groups = self._getGroups(False)
        return self._exportGroups(groups)

    def service_getAllGroups(self, context):
        """
        Get all system groups as list of (name, gid): (unicode, str).
        """
        return deferToThread(self._getAllGroups)

    def service_setUseNND(self, context, use_nnd):
        self._setUseNND(use_nnd)

    def _setUseNND(self, use_nnd):
        self.use_nnd = getBoolean(use_nnd)
        self.debug("Use NND: %s" % self.use_nnd)
        storage = VariablesStore()
        storage['use_nnd'] = self.use_nnd
        storage.save(STORAGE_FILENAME)

