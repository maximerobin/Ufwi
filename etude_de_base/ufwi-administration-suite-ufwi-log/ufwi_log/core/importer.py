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

import pickle
from twisted.internet.defer import DeferredList

from ufwi_rpcd.backend.cron import scheduleRepeat
from ufwi_rpcd.backend.logger import Logger
from ufwi_rpcd.backend.error import RpcdError

from exporter import Exporter

class Importer(Logger):

    rotation_period = 3600*24

    def __init__(self, core):
        Logger.__init__(self, "Importer")

        self.core = core
        self.database = None
        self.imported_rotation = 0
        self.cron = scheduleRepeat(self.rotation_period, self.rotate_table)

    def rehash(self, conf):
        """
        Rehash configuration, and (re)start cron job.

        If period == 0, job is disabled.
        """
        self.imported_rotation = int(conf.get('import_rotation'))

    def rotate_table(self):
        if self.imported_rotation == 0:
            return

        request = self.database.createRequest()
        return self.database.query(request.rotate_imported(self.imported_rotation))

    def receivedExport(self, data, firewall, dist_meta):
        if not self.database:
            raise RpcdError("Unable to import data: no database selected.")
        if not self.imported_rotation:
            raise RpcdError("Importing data is disabled.")

        local_meta = Exporter.getMeta(data)
        local_meta = (Exporter.PROTO_VERSION,) + local_meta

        try:
            dist_meta = tuple(dist_meta)
        except TypeError:
            raise RpcdError('Invalid arguments')

        if dist_meta[0] > local_meta[0]:
            # It uses a newer protocol than me, I ask it to use my protocol.
            return Exporter.PROTO_VERSION
        elif dist_meta[0] < local_meta[0]:
            # use the distant protocol version
            local_meta = (dist_meta[0],) + local_meta[1:]

        if local_meta != dist_meta:
            self.warning('Received invalid export data from %s: %r != %r' % (firewall, local_meta, dist_meta))
            return False

        try:
            table = pickle.loads(data)
        except Exception, err:
            self.error("Data received from %s are invalid: %s" % err)
            return False

        deferredlist = []
        for line in table:
            args = []
            for value in line:
                s = ''
                if isinstance(value, bool):
                    s = 'TRUE' if value else 'FALSE'
                elif isinstance(value, (long,int)):
                    s = '%d' % value
                elif value is None:
                    s = 'NULL'
                else:
                    s = self.database.escape('%s' % value)

                args.append(s)

            request = self.database.createRequest()
            d = self.database.query(request.insert_imported_data(dist_meta[0], firewall, args))
            d.addErrback(self.exportError)
            deferredlist.append(d)

        deferredlist = DeferredList(deferredlist)
        deferredlist.addCallback(lambda *args: True)
        deferredlist.addErrback(self.exportError)

        return deferredlist

    def exportError(self, err):
        self.writeError(err)
        raise RpcdError("An error occured during importing data into database.")
