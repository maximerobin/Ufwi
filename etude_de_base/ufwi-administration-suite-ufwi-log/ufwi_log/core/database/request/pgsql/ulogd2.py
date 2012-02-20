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

class Ulogd2Request(IRequest):
    def is_multisite(self):
        return True

    def raw_label2i(self, raw_label):
        return raw_label

    def __init__(self, database, tablename):
        IRequest.__init__(self, database, tablename)
        self.nufw_view = 'view_ufwi_log%s' % self.sufix

    def gettable(func):
        def inner(self, filters, *args, **kwargs):
            if 'username' in filters.filters or \
               'client_app' in filters.filters or \
               'client_os' in filters.filters:
                tablename = self.nufw_view
            else:
                tablename = self.ulog

            return func(self, filters, tablename, *args, **kwargs)

        return inner

    def rotate_imported(self, period):
        return """DELETE FROM %s WHERE %s >= %s AND firewall != ''""" % (self.ulog,
                                                     self.getfield('timestamp'),
                                                     ('%s - %d' % (self.database.kw_timestamp % 'Now()', int(period))))

    def select_exportable_data(self, proto, begin, end):
        # use proto variable for next features
        return """SELECT mac_str, oob_time_sec, oob_time_usec, oob_prefix, oob_mark, oob_in, oob_out,
                        ip_saddr_str, ip_daddr_str, ip_protocol, ip_tos, ip_ttl, ip_totlen, ip_ihl,
                        ip_csum, ip_id, ip_fragoff, tcp_sport, tcp_dport, tcp_seq, tcp_ackseq, tcp_window,
                        tcp_urg, tcp_urgp, tcp_ack, tcp_psh, tcp_rst, tcp_syn, tcp_fin, udp_sport,
                        udp_dport, udp_len, icmp_type, icmp_code, icmp_echoid, icmp_echoseq, icmp_gateway,
                        icmp_fragmtu, timestamp, raw_label, username, client_os, client_app
                        FROM view_ufwi_log WHERE %s >= %s and %s < %s""" \
                                % (self.getfield('timestamp'),
                                   int(begin),
                                   self.getfield('timestamp'),
                                   int(end))

    def insert_imported_data(self, proto, firewall, args):

        # use proto variable for next features
        ulog2_args = ','.join(args[:40])
        nufw_args = ','.join(args[40:])
        s = """INSERT INTO ulog2 (firewall, mac_str, oob_time_sec,
                        oob_time_usec, oob_prefix, oob_mark, oob_in, oob_out,
                        ip_saddr_str, ip_daddr_str, ip_protocol, ip_tos, ip_ttl,
                        ip_totlen, ip_ihl, ip_csum, ip_id, ip_fragoff, tcp_sport,
                        tcp_dport, tcp_seq, tcp_ackseq, tcp_window, tcp_urg,
                        tcp_urgp, tcp_ack, tcp_psh, tcp_rst, tcp_syn, tcp_fin,
                        udp_sport, udp_dport, udp_len, icmp_type, icmp_code,
                        icmp_echoid, icmp_echoseq, icmp_gateway, icmp_fragmtu,
                        timestamp, raw_label) VALUES (%s, %s);""" \
                          % (self.database.escape(firewall), ulog2_args)

        if args[40] != 'NULL' and args[41] != 'NULL' and args[42] != 'NULL' and args[43] != 'NULL':
            s += """INSERT INTO nufw (_nufw_id, username, client_os, client_app)
                      VALUES (currval('ulog2__id_seq'), %s)""" % nufw_args

        return s

    @gettable
    def select_packets(self, filters, table):
        """ Method used to select all packets which matches "where" clause. """

        return """SELECT _id as packet_id, username, ip_saddr_str, ip_daddr_str,
                    ip_protocol as proto,
                    COALESCE(tcp_sport, udp_sport) as sport,
                    COALESCE(tcp_dport, udp_dport) as dport,
                    oob_time_sec, oob_prefix, raw_label
                    FROM %s
                    %s""" % (self.nufw_view, filters.getwhere())

    @gettable
    def count_packets(self, filters, table):

        return """SELECT COUNT(*) FROM %s %s """ % (table, filters.getwhere())

    @gettable
    def get_packet(self, filters, table, _id):
        """ Get a specific packet with his _id """

        return """SELECT _id as packet_id, username, oob_time_sec, oob_time_usec, oob_in, oob_out,
                        oob_prefix, oob_mark, ip_saddr_str, ip_daddr_str, ip_tos, ip_ttl, ip_totlen,
                        ip_ihl, ip_csum, ip_id, ip_protocol as proto, raw_label,
                        COALESCE(tcp_sport, udp_sport) as sport,
                        COALESCE(tcp_dport, udp_dport) as dport,
                        tcp_seq, tcp_ackseq, tcp_window, tcp_urg, tcp_urgp, tcp_ack, tcp_psh, tcp_rst, tcp_syn, tcp_fin,
                        udp_len, icmp_type, icmp_code, client_os, client_app, 0 AS packets_in, 0 AS packets_out,
                        0 AS bytes_in, 0 AS bytes_out, mac_saddr_str::varchar, mac_daddr_str::varchar, mac_str
                    FROM %s
                    WHERE _id = %s
                """ % (self.nufw_view, _id)

    @gettable
    def select_conusers(self, filters, table, group_user=False):
        """ Get all connected users """

        group = 'GROUP BY username' if group_user else ''
        return """SELECT username, ip_saddr_str, os_sysname, session_start_time, session_end_time
                    FROM users_ufwi_log%s
                    %s %s""" % (self.sufix, filters.getwhere(), group)

    @gettable
    def select_authfail(self, filters, table):
        """ Get all authentication failed users """

        delta = None
        if 'start_time' in filters.filters and 'end_time' in filters.filters:
            delta = filters.filters['end_time'] - filters.filters['start_time']

        if not delta:
            return ""

        where = filters.getwhere()
        return  """SELECT username, ip_saddr_str, reason, time FROM authfail
                %s
                GROUP BY username, ip_saddr_str, reason, time""" % (where)

    @gettable
    def select_ports(self, filters, table, proto):
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
                """ % (proto, table, where, proto)

    @gettable
    def count_port(self, filters, table, proto):
        """ Count number of dropped ports on this protocol
            @param proto [string] 'tcp' or 'udp'
        """

        where = filters.getwhere()
        if where:
            where += ' AND %s_dport IS NOT NULL' % proto
        else:
            where = 'WHERE %s_dport IS NOT NULL' % proto

        return """SELECT COUNT(*) FROM %s %s""" % (table, where)

    @gettable
    def select_ip(self, filters, table, direction):
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
                """ % (direction, table, where, direction)

    @gettable
    def count_ip(self, filters, table, direction):
        """ Count all dropped packets """

        where = filters.getwhere()
        if where:
            where += ' AND ip_%saddr_str IS NOT NULL' % direction
        else:
            where = 'WHERE ip_%saddr_str IS NOT NULL' % direction

        return """SELECT COUNT(*) FROM %s %s""" % (table, where)

    @gettable
    def select_apps(self, filters, table):

        where = filters.getwhere()
        if where:
            where += ' AND client_app IS NOT NULL'
        else:
            where = 'WHERE client_app IS NOT NULL'

        return """SELECT client_app, COUNT(*) AS packets, MIN(oob_time_sec) AS start_time, MAX(oob_time_sec) AS end_time
                    FROM %s
                    %s
                    GROUP BY client_app
                """ % (self.nufw_view, where)

    @gettable
    def count_apps(self, filters, table):
        """ Count all dropped packets """

        where = filters.getwhere()
        if where:
            where += ' AND client_app IS NOT NULL'
        else:
            where = 'WHERE client_app IS NOT NULL'

        return """SELECT COUNT(*) FROM %s %s""" % (self.nufw_view, where)

    @gettable
    def select_user(self, filters, table):
        """ List all users who have dropped packets """

        where = filters.getwhere()
        return """SELECT username, COUNT(*) AS packets,
                         MIN(oob_time_sec) AS start_time, MAX(oob_time_sec) AS end_time
                    FROM %s
                    %s
                    AND username IS NOT NULL
                    GROUP BY username
                """ % (self.nufw_view, where)

    @gettable
    def count_user(self, filters, table):
        """ Count all users packets which are dropped """

        where = filters.getwhere()

        return """SELECT COUNT(*) FROM %s %s""" % (self.nufw_view, where)

    @gettable
    def select_traffic(self, filters, table):

        return "SELECT 0 AS bytes_in, 0 AS bytes_out "

    @gettable
    def select_tuple(self, filters, table, field1, field2):

        return """SELECT %s, %s, COUNT(*) AS packets, MIN(oob_time_sec) AS start_time, MAX(oob_time_sec) AS end_time
                  FROM %s
                  %s
                  GROUP BY %s, %s
               """ % (self.getfield(field1), self.getfield(field2), self.nufw_view, filters.getwhere(), self.getfield(field1), self.getfield(field2))

    @gettable
    def select_badhosts(self, filters, table):

        return """SELECT ip_saddr_str, count(*)/300 as RATE
                  FROM %s
                  WHERE (oob_time_sec > EXTRACT(epoch FROM NOW() - INTERVAL '5 MINUTES')::integer) AND raw_label = 0
                  GROUP BY ip_saddr_str""" % self.nufw_view

    @gettable
    def select_badusers(self, filters, table):

       return """SELECT username, count(*)/300 as RATE
                  FROM %s
                  WHERE (oob_time_sec > EXTRACT(epoch FROM now() - INTERVAL '5 MINUTES')::integer) AND username IS NOT NULL AND raw_label = 0
                  GROUP BY username""" % self.nufw_view

    @gettable
    def count_average(self, filters, table, minutes):

        where = filters.getwhere()
        if where:
            where += ' AND oob_time_sec >= (EXTRACT(epoch FROM Now()) - %d)::integer' % (minutes*60)
        else:
            where = 'WHERE oob_time_sec >= (EXTRACT(epoch FROM Now()) - %d)::integer' % (minutes*60)

        return """SELECT COUNT(*)/%d FROM %s %s""" % (minutes*60, table, where)

    @gettable
    def select_userid(self, filters, table):

        where = filters.getwhere()
        if where:
            where += ' AND username IS NOT NULL'
        else:
            where = 'WHERE username IS NOT NULL'

        return """SELECT username
                  FROM %s
                  %s
                  GROUP BY username""" % (self.nufw_view, where)

    @gettable
    def select_userid_auth(self, filters, table):

        where = filters.getwhere()
        if where:
            where += ' AND username IS NOT NULL'
        else:
            where = 'WHERE username IS NOT NULL'

        return """SELECT username
                  FROM %s
                  %s
                  GROUP BY username""" % (self.nufw_view, where)


    def squid_select_requests(self, filters):
        return """SELECT ip_saddr_str, raw_label AS proxy_state, _size AS volume, url, timestamp as oob_time_sec
                  FROM squid
                  %s""" % (filters.getwhere())

    def squid_select_users(self, filters):
        where = filters.getwhere()
        if where:
            where += ' AND username IS NOT NULL'
        else:
            where = 'WHERE username IS NOT NULL'

        return """SELECT username as proxy_username, COUNT(*) AS requests,
                         SUM(_size) AS volume,
                         MIN(timestamp) AS start_time, MAX(timestamp) AS end_time
                    FROM squid
                    %s
                    GROUP BY proxy_username
                """ % (where)

    def squid_count_users(self, filters):
        where = filters.getwhere()
        if where:
            where += ' AND username IS NOT NULL'
        else:
            where = 'WHERE username IS NOT NULL'

        return """SELECT COUNT(*) FROM squid %s""" % (where)

    def squid_select_ipaddress(self, filters):
        where = filters.getwhere()
        if where:
            where += ' AND ip_saddr_str IS NOT NULL'
        else:
            where = 'WHERE ip_saddr_str IS NOT NULL'

        return """SELECT ip_saddr_str, COUNT(*) AS requests,
                         SUM(_size) AS volume,
                         MIN(timestamp) AS start_time, MAX(timestamp) AS end_time
                    FROM squid
                    %s
                    GROUP BY ip_saddr_str
                """ % (where)

    def squid_count_ipaddress(self, filters):
        where = filters.getwhere()
        if where:
            where += ' AND ip_saddr_str IS NOT NULL'
        else:
            where = 'WHERE ip_saddr_str IS NOT NULL'

        return """SELECT COUNT(*) FROM squid %s""" % (where)

    def squid_select_domains(self, filters):
        where = filters.getwhere()
        if where:
            where += ' AND domain IS NOT NULL'
        else:
            where = 'WHERE domain IS NOT NULL'

        return """SELECT domain, COUNT(*) AS requests,
                         SUM(_size) AS volume,
                         MIN(timestamp) AS start_time, MAX(timestamp) AS end_time
                    FROM squid
                    %s
                    GROUP BY domain
                """ % (where)

    def squid_count_domains(self, filters):
        where = filters.getwhere()
        if where:
            where += ' AND domain IS NOT NULL'
        else:
            where = 'WHERE domain IS NOT NULL'

        return """SELECT COUNT(*) FROM squid %s""" % (where)


