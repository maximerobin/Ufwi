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

from ufwi_log.core.database.request import mysql

class UlogRequest(mysql.UlogRequest):
    def select_badhosts(self, filters):

        return """SELECT ip_saddr_str, count(*)/300 as RATE
                  FROM %s
                  WHERE (oob_time_sec > EXTRACT(epoch FROM NOW() - 'INTERVAL 5 MINUTE')) AND raw_label = 0
                  GROUP BY ip_saddr_str""" % self.ulog

    def select_badusers(self, filters):

        return """SELECT username, count(*)/300 as RATE
                  FROM %s
                  WHERE oob_time_sec > EXTRACT(epoch FROM NOW()) - 'INTERVAL 5 MINUTE')) AND username IS NOT NULL AND raw_label=0
                  GROUP BY username""" % self.ulog


    def count_average(self, filters, minutes):

        where = filters.getwhere()
        if where:
            where += ' AND oob_time_sec >= EXTRACT(epoch FROM Now()) - %d' % (minutes*60)
        else:
            where = 'WHERE oob_time_sec >= EXTRACT(epoch FROM Now()) - %d' % (minutes*60)

        return """SELECT COUNT(*)/%d FROM %s %s""" % (minutes*60, self.ulog, where)

