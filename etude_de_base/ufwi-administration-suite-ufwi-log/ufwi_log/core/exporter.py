# -*- coding: utf-8 -*-

"""
Copyright (C) 2007-2011 EdenWall Technologies
Written by Romain Bignon <romain AT inl.fr>

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

import os
from ufwi_rpcd.backend.cron import scheduleRepeat
from ufwi_rpcd.backend.logger import Logger
from ufwi_rpcd.backend.variables_store import VariablesStore
from ufwi_rpcd.backend.exceptions import ConfigError

import hashlib
import time
import cPickle as pickle

class Exporter(Logger):

    # This is the default value of lastsync, at first launch.
    # TODO It is important to determine what value to use, because
    #      when value is 0, Exporter sends all entries in database,
    #      instead of nothing when value is now.
    #LASTSYNC_DEFAULT = 0
    LASTSYNC_DEFAULT = time.time()
    PROTO_VERSION = 1
    CONFIG_FILE = 'ufwi_log_export.xml'

    def __init__(self, context, core):
        Logger.__init__(self, "Exporter")

        self.core = core
        self.context = context
        self.cron = None
        self.locked = False
        self.period = 0
        self.rotation_period = 3600*24*30
        self.sync_start = 0
        self.server_proto = self.PROTO_VERSION

        self.config = VariablesStore()
        self.config_path = os.path.join(self.core.config.get('CORE', 'vardir'), self.CONFIG_FILE)

        try:
            self.config.load(self.config_path)
            self.lastsync = int(self.config.get('lastsync'))
        except (ValueError,ConfigError):
            self.lastsync = self.LASTSYNC_DEFAULT

    @staticmethod
    def getMeta(data):
        md5 = hashlib.md5(data).hexdigest()
        sha1 = hashlib.sha1(data).hexdigest()
        sha256 = hashlib.sha256(data).hexdigest()
        size = len(data)

        return md5, sha1, sha256, size

    def rehash(self, conf):
        """
        Rehash configuration, and (re)start cron job.

        If period == 0, job is disabled.
        """
        period = int(conf.get('export_period'))
        if period == self.period:
            return

        self.period = period
        if self.period:
            self.start()
        else:
            self.stop()

    def stop(self):
        if self.cron:
            self.cron.stop()
            self.cron = None
        self.locked = False

    def start(self):
        self.stop()
        self.cron = scheduleRepeat(self.period, self.export_table)

    def export_table(self):
        if not self.database:
            self.warning('Not connected anywhere.')
            return

        now = time.time()

        # As last synchronization is older than rotation period,
        # it is possible that some data are lost.
        if self.lastsync < now - self.rotation_period:
            self.warning("Some data are probably lost.")

        if self.lastsync > now - self.period:
            return

        if self.locked:
            return

        self.locked = True
        self.sync_start = time.time()

        begin, end = self.lastsync, self.lastsync+self.period

        request = self.database.createRequest()
        d = self.database.query(request.select_exportable_data(self.server_proto, begin, end))
        d.addCallback(self.publish_data)
        d.addErrback(self.publish_err)
        return d

    def publish_data(self, (result, size)):
        if not result:
            return self.next_rotation()

        data = pickle.dumps(result)
        meta = Exporter.getMeta(data)
        meta = (self.server_proto,) + meta

        return self.core.callService(self.context, 'multisite_transport', 'hostFile', data).addCallback(self.send_url, meta).addErrback(self.publish_err)

    def send_url(self, path, meta):
        return self.core.callService(self.context, 'multisite_slave', 'callRemote', 'ufwi_log', 'export',
                              path, meta).addCallback(self.publish_ack, path).addErrback(self.publish_err, path)

    def publish_ack(self, result, path):
        self.core.callService(self.context, 'multisite_transport', 'removeFile', path)
        self.locked = False
        if not result is True:
            if isinstance(result, (int,long)):
                # It asks me to use an older protocol version
                self.server_proto = result
            else:
                self.error('An error occured on EMS while receiving data. Retrying...')
            return

        self.next_rotation()

    def next_rotation(self):
        self.lastsync += self.period
        self.locked = False

        # Store in config
        self.config.set('lastsync', int(self.lastsync))
        self.config.save(self.config_path)

        if (time.time() - self.sync_start) >= self.period:
            self.error("Export takes more time than period (%ds >= %ds). Cron is disabled" % (time.time() - self.sync_start, self.period))
            self.period = 0
            self.stop()
            return

        if (time.time() - self.lastsync) >= self.period:
            # We can do that a second time.
            self.export_table()

    def publish_err(self, e, path=''):
        self.error("An error occured during data exportation to EMF appliance: %s" % e)
        if path:
            self.core.callService(self.context, 'multisite_transport', 'removeFile', path)
        self.locked = False
