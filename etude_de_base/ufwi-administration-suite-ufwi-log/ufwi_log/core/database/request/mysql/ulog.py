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

from ufwi_log.core.database.request.base import IRequest

class UlogRequest(IRequest):

    def raw_label2i(self, raw_label):
        return 3 if raw_label else 0

    def rotate_imported(self, period):
        return """DELETE FROM %s WHERE %s >= %s""" % (self.ulog,
                                                      self.database.kw_timestamp % 'timestamp',
                                                     ('%s - %d' % (self.database.kw_timestamp % 'Now()', int(period))))

    def select_exportable_data(self, proto, begin, end):
        # use proto variable for next features
        return """SELECT raw_mac, oob_time_sec, oob_time_usec, oob_prefix, oob_mark, oob_in, oob_out,
                        ip_saddr_str, ip_daddr_str, ip_protocol, ip_tos, ip_ttl, ip_totlen, ip_ihl,
                        ip_csum, ip_id, ip_fragoff, tcp_sport, tcp_dport, tcp_seq, tcp_ackseq, tcp_window,
                        tcp_urg, tcp_urgp, tcp_ack, tcp_psh, tcp_rst, tcp_syn, tcp_fin, udp_sport,
                        udp_dport, udp_len, icmp_type, icmp_code, icmp_echoid, icmp_echoseq, icmp_gateway,
                        icmp_fragmtu, pwsniff_user, pwsniff_pass, ahesp_spi, timestamp, raw_label, end_timestamp,
                        start_timestamp, username, client_os, client_app
                        FROM %s WHERE timestamp >= %s and timestamp < %s""" \
                                % (self.ulog,
                                   self.database.kw_datetime % int(begin),
                                   self.database.kw_datetime % int(end))

    def insert_imported_data(self, proto, firewall, args):
        # use proto variable for next features
        return """INSERT INTO %s (firewall, raw_mac, oob_time_sec,
                        oob_time_usec, oob_prefix, oob_mark, oob_in, oob_out,
                        ip_saddr_str, ip_daddr_str, ip_protocol, ip_tos, ip_ttl,
                        ip_totlen, ip_ihl, ip_csum, ip_id, ip_fragoff, tcp_sport,
                        tcp_dport, tcp_seq, tcp_ackseq, tcp_window, tcp_urg,
                        tcp_urgp, tcp_ack, tcp_psh, tcp_rst, tcp_syn, tcp_fin,
                        udp_sport, udp_dport, udp_len, icmp_type, icmp_code,
                        icmp_echoid, icmp_echoseq, icmp_gateway, icmp_fragmtu,
                        pwsniff_user, pwsniff_pass, ahesp_spi, timestamp, raw_label,
                        end_timestamp, start_timestamp, username,
                        client_os, client_app) VALUES (%s, %s)""" % \
                            (self.ulog, self.database.escape(firewall), ','.join(args))

    def select_packets(self, filters):
        """ Method used to select all packets which matches "where" clause. """

        table = self.ulog

        return """SELECT _id as packet_id, username, ip_saddr_str, ip_daddr_str,
                    ip_protocol as proto,
                    COALESCE(tcp_sport, udp_sport) as sport,
                    COALESCE(tcp_dport, udp_dport) as dport,
                    oob_time_sec, oob_prefix, raw_label
                    FROM %s
                    %s""" % (table, filters.getwhere())

    def count_packets(self, filters):
        return """SELECT COUNT(*) FROM %s %s """ % (self.ulog, filters.getwhere())

    def get_packet(self, filters, _id):
        """ Get a specific packet with his _id """

        return """SELECT _id as packet_id, username, oob_time_sec, oob_time_usec, oob_in, oob_out,
                        oob_prefix, oob_mark, ip_saddr_str, ip_daddr_str, ip_tos, ip_ttl, ip_totlen,
                        ip_ihl, ip_csum, ip_id, ip_protocol as proto, raw_label,
                        COALESCE(tcp_sport, udp_sport) as sport,
                        COALESCE(tcp_dport, udp_dport) as dport,
                        tcp_seq, tcp_ackseq, tcp_window, tcp_urg, tcp_urgp, tcp_ack, tcp_psh, tcp_rst, tcp_syn, tcp_fin,
                        udp_len, icmp_type, icmp_code, client_os, client_app, bytes_in, bytes_out,
                        packets_in, packets_out, raw_mac
                    FROM %s
                    WHERE _id = %s
                """ % (self.ulog, _id)

    def select_conusers(self, filters):
        """ Get all connected users """

        return """SELECT username, ip_saddr_str, os_sysname, start_time, end_time
                    FROM users%s
                    %s""" % (self.sufix, filters.getwhere())

    def select_ports(self, filters, proto):
        """ List all ports """

        where = filters.getwhere()
        if where:
            where += ' AND %s_dport IS NOT NULL' % proto
        else:
            where = 'WHERE %s_dport IS NOT NULL' % proto

        return """SELECT %s_dport, COUNT(*) AS packets, MIN(oob_time_sec) AS start_time, MAX(oob_time_sec) AS end_time
                    FROM %s
                    %s
                    GROUP BY %s_dport
                """ % (proto, self.ulog, where, proto)

    def count_port(self, filters, proto):
        """ Count number of dropped ports on this protocol
            @param proto [string] 'tcp' or 'udp'
        """

        where = filters.getwhere()

        if where:
            where += ' AND %s_dport IS NOT NULL' % proto
        else:
            where = 'WHERE %s_dport IS NOT NULL' % proto

        return """SELECT COUNT(*) FROM %s %s""" % (self.ulog, where)

    def select_ip(self, filters, direction):
        """ List all ips which matches filters """

        where = filters.getwhere()
        if where:
            where += ' AND ip_%saddr_str IS NOT NULL' % direction
        else:
            where = 'WHERE ip_%saddr_str IS NOT NULL' % direction

        return """SELECT ip_%saddr_str, COUNT(*) AS packets, MIN(oob_time_sec) AS start_time, MAX(oob_time_sec) AS end_time
                    FROM %s
                    %s
                    GROUP BY ip_%saddr_str
                """ % (direction, self.ulog, where, direction)

    def count_ip(self, filters, direction):
        """ Count all dropped packets """

        where = filters.getwhere()
        if where:
            where += ' AND ip_%saddr_str IS NOT NULL' % direction
        else:
            where = 'WHERE ip_%saddr_str IS NOT NULL' % direction

        return """SELECT COUNT(*) FROM %s %s""" % (self.ulog, where)

    def select_apps(self, filters):

        where = filters.getwhere()
        if where:
            where += ' AND client_app IS NOT NULL'
        else:
            where = 'WHERE client_app IS NOT NULL'

        return """SELECT client_app, COUNT(*) AS packets, MIN(oob_time_sec) AS start_time, MAX(oob_time_sec) AS end_time
                    FROM %s
                    %s
                    GROUP BY client_app
                """ % (self.ulog, where)

    def count_apps(self, filters):
        """ Count all dropped packets """

        where = filters.getwhere()
        if where:
            where += ' AND client_app IS NOT NULL'
        else:
            where = 'WHERE client_app IS NOT NULL'

        return """SELECT COUNT(*) FROM %s %s""" % (self.ulog, where)

    def select_user(self, filters):
        """ List all users who have dropped packets """

        where = filters.getwhere()

        return """SELECT username, COUNT(*) AS packets,
                         MIN(oob_time_sec) AS start_time, MAX(oob_time_sec) AS end_time
                    FROM %s
                    %s
                    GROUP BY username
                """ % (self.ulog, where)

    def count_user(self, filters):
        """ Count all users packets which are dropped """

        where = filters.getwhere()

        return """SELECT COUNT(*) FROM %s %s""" % (self.ulog, where)

    def select_traffic(self, filters):

        return """SELECT SUM(bytes_in) AS bytes_in, SUM(bytes_out) AS bytes_out
                    FROM %s
                    %s
               """ % (self.ulog, filters.getwhere())

    def select_tuple(self, filters, field1, field2):

        return """SELECT %s, %s, COUNT(*) AS packets, MIN(oob_time_sec) AS start_time, MAX(oob_time_sec) AS end_time
                  FROM %s
                  %s
                  GROUP BY %s, %s
               """ % (field1, field2, self.ulog, filters.getwhere(), field1, field2)

    def select_badhosts(self, filters):

        return """SELECT ip_saddr_str, count(*)/300 as RATE
                  FROM %s
                  WHERE (oob_time_sec > NOW() - INTERVAL 5 MINUTE) AND raw_label = 0
                  GROUP BY ip_saddr_str""" % self.ulog

    def select_badusers(self, filters):

        return """SELECT username, count(*)/300 as RATE
                  FROM %s
                  WHERE oob_time_sec > NOW()- INTERVAL 5 MINUTE AND username NOT LIKE \"\" AND raw_label=0
                  GROUP BY username""" % self.ulog

    def count_average(self, filters, minutes):

        where = filters.getwhere()
        if where:
            where += ' AND oob_time_sec >= UNIX_TIMESTAMP(Now()) - %d' % (minutes*60)
        else:
            where = 'WHERE oob_time_sec >= UNIX_TIMESTAMP(Now()) - %d' % (minutes*60)

        return """SELECT COUNT(*)/%d FROM %s %s""" % (minutes*60, self.ulog, where)

    def select_userid(self, filters):

        where = filters.getwhere()
        if where:
            where += ' AND username IS NOT NULL'
        else:
            where = 'WHERE username IS NOT NULL'

        return """SELECT username
                  FROM %s
                  %s
                  GROUP BY username""" % (self.ulog, where)
