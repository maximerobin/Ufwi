# -*- coding: utf-8 -*-
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

from ufwi_rpcd.backend import Component
from nuauth_command import NuauthError, Client
from ufwi_rpcd.backend.anonymization import anonymizer

def timedeltaSeconds(delta):
    return delta.seconds + delta.days * 3600 * 24

class NuauthCommand(Component):
    NAME = "nuauth_command"
    VERSION = "1.0"
    API_VERSION = 2

    ROLES = {'nuauth_command_read': set((
                    'getNuauthVersion', 'getUptime', 'getUsers',
                    'getFirewalls', 'getPacketCount',
                    'getDebugLevel', 'getDebugAreas', 'getUsersCount'
                )),
             'nuauth_command_write': set((
                    '@nuauth_command_read',
                    'disconnect', 'disconnectAll', 'reload', 'refreshCache',
                    'setDebugLevel', 'setDebugAreas'
                )),
            }

    def init(self, core):
        self.socket_filename = "/var/run/nuauth/nuauth-command.socket"
        self.client = None

    def getClient(self):
        return self.client

    def _command(self, command):
        if not self.client:
            # Create and connect client
            self.client = Client(self.socket_filename)
            try:
                self.client.connect()
            except NuauthError, err:
                self.client = None
                raise

        # Execute command and convert answer to string
        if not self.client:
            self.client = Client(self.socket_filename)
            try:
                self.client.connect()
            except NuauthError, err:
                self.client = None
                raise

        result = self.client.execute(command)
        result = result.content
        return result

    def service_getNuauthVersion(self, context):
        """Get nuauth version string"""
        return self._command("version")

    def service_getUptime(self, context):
        """Get nuauth uptime"""
        uptime = self._command("uptime")
        return {
            'start': unicode(uptime.start),
            'seconds': timedeltaSeconds(uptime.diff),
        }

    def service_getUsers(self, context):
        """Get the list of connected NuFW users"""
        users = []
        for user in self._command("users"):
            users.append({
                'name': anonymizer.anon_username(context, unicode(user.name)),
                'uid': anonymizer.anon_userid(context, int(user.uid)),
                'addr': anonymizer.anon_ipaddr(context, unicode(user.addr)),
                'sock': int(user.socket),
                'sport': int(user.sport),
                'groups': [unicode(group) for group in user.groups],
                'connect_timestamp': unicode(user.connect_timestamp),
                'uptime': unicode(user.uptime),
                'expire': user.expire or '', # it can be None
                'sysname': unicode(user.sysname),
                'release': unicode(user.release),
                'version': unicode(user.version),
                'activated': unicode(user.activated),
                'client_version': unicode(user.client_version),
            })
        return users

    def service_getUsersCount(self, context):
        return self._command("user count")

    def service_getFirewalls(self, context):
        """Get the list of connected firewalls"""
        return self._command("firewalls")

    def service_getPacketCount(self, context):
        """Get number of decision waiting packets"""
        return self._command("packets count")

    def service_refreshCache(self, context):
        """Ask server to refresh all caches"""
        return self._command("refresh cache")

    def service_refreshCRL(self, context):
        return self._command("refresh crl")

    def service_disconnect(self, context, user_id):
        """Disconnect specified user"""
        return self._command("disconnect %s" % user_id)

    def service_disconnectAll(self, context):
        """Disconnect all users"""
        return self._command("disconnect all")

    def service_reload(self, context):
        """Reload server configuration"""
        return self._command("reload")

    def service_getDebugLevel(self, context):
        """Get debug level"""
        return self._command("display debug_level")

    def service_getDebugAreas(self, context):
        """Get debug areas"""
        return self._command("display debug_areas")

    def service_setDebugLevel(self, context, areas):
        """Set debug level"""
        return self._command("debug_level %s" % areas)

    def service_setDebugAreas(self, context, areas):
        """Set debug areas"""
        return self._command("debug_areas %s" % areas)

