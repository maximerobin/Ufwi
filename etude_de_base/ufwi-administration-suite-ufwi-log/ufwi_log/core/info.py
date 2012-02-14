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

from tablebase import InfoBase
from ufwi_rpcd.backend.anonymization import anonymizer

class PacketInfo(InfoBase):
    """ Get informations on ONE packet """

    columns = ['packet_id', 'username', 'oob_time_sec', 'oob_time_usec', 'oob_in', 'oob_out', 'oob_prefix',
               'oob_mark', 'ip_saddr_str', 'ip_daddr_str', 'ip_tos', 'ip_ttl', 'ip_totlen', 'ip_ihl', 'ip_csum',
               'ip_id', 'proto', 'raw_label', 'sport', 'dport', 'tcp_seq', 'tcp_ackseq', 'tcp_window', 'tcp_urg',
               'tcp_urgp', 'tcp_ack', 'tcp_psh', 'tcp_rst', 'tcp_syn', 'tcp_fin', 'udp_len',
               'icmp_type', 'icmp_code', 'client_os', 'client_app', 'bytes_in', 'bytes_out',
               'packets_in', 'packets_out', 'mac_saddr_str', 'mac_daddr_str', 'raw_mac']

    def entry_form(self, entry):
        """ We transform IP form to a string
            @param entry [tuple]
            @return [tuple]

            id, username, oob_time_sec, oob_time_usec, oob_in, oob_out, oob_prefix, oob_mark, ip_saddr_str,
            ip_daddr_str, ...
        """
        result = (entry[0],)
        result += (anonymizer.anon_username(self.ctx, entry[1]),)

        result += entry[2:8]
        result += (anonymizer.anon_ipaddr(self.ctx, self.ip2str(entry[8])),)
        result += (anonymizer.anon_ipaddr(self.ctx, self.ip2str(entry[9])),)
        result += entry[10:16]
        result += (self.proto2str(entry[16]),)
        result += (1 if entry[17] else 0,)
        result += entry[18:34]
        result += (anonymizer.anon_appname(self.ctx, entry[34]),)
        result += entry[35:]

        return result

    def __call__(self, **args):
        """
            @param id [integer] Packet ID
        """
        self._arg_int(args, 'packet_id')

        # Used for see packets in archives. (InfoBase will see at args['start_time'] and args['end_time'])
        for name in ('start_time', 'end_time'):
            try:
                self.args[name] = int(args[name])
            except:
                pass

        result = self._sql_query(args, "get_packet", self.args['packet_id'])

        result.addCallback(self._print_result)
        return result
