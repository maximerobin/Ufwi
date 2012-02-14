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

from .ulog import UlogRequest

# TODO IT DOESN'T WORK
class Ulogd2Request(UlogRequest):

    def is_multisite(self):
        return True

    def raw_label2i(self, raw_label):
        return raw_label

    def select_traffic(self, filters):

        return 'SELECT 0, 0'

    def get_packet(self, filters, _id):
        """ Get a specific packet with his _id """

        return """SELECT _id as packet_id, username, user_id, oob_time_sec, oob_time_usec, oob_in, oob_out,
                        oob_prefix, oob_mark, ip_saddr_str, ip_daddr_str, ip_tos, ip_ttl, ip_totlen,
                        ip_ihl, ip_csum, ip_id, ip_protocol as proto, raw_label,
                        COALESCE(tcp_sport, udp_sport) as sport,
                        COALESCE(tcp_dport, udp_dport) as dport,
                        tcp_seq, tcp_ackseq, tcp_window, tcp_urg, tcp_urgp, tcp_ack, tcp_psh, tcp_rst, tcp_syn, tcp_fin,
                        udp_len, icmp_type, icmp_code, client_os, client_app, raw_mac
                    FROM %s
                    WHERE _id = %s
                """ % (self.ulog, _id)


