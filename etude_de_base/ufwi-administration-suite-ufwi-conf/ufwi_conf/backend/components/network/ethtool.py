
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

import re

from ufwi_rpcd.common.error import exceptionAsUnicode
from ufwi_rpcd.backend.logger import Logger

from ufwi_conf.backend.output_parser import OutputStructure, Parser, NotAllowed

ETHTOOL_TIMEOUT = 5 #seconds
ERROR_KEY = 'ethtool_error'

class NoSuchDevice(Exception):
    pass

class Ethtool(Logger):
    #Return codes guessed without doc...
    RETCODES = {
    71: 'NO_SUCH_IFACE',
    75: 'NO_SUCH_IFACE',
    76: 'NO_SUCH_IFACE',
    97: 'NOT_ALLOWED'
    }
    def __init__(self, ethtool_exe, parent_logger):
        Logger.__init__(self, 'ethtool', parent = parent_logger)
        self.ethtool_exe = ethtool_exe

        self.show_ring = self.init_show_ring()
        self.statistics = self.init_statistics()
        self.nooptions = self.init_nooptions()

    def formatError(self, error):
        retcode = exceptionAsUnicode(error)
        if retcode in Ethtool.RETCODES:
            return {ERROR_KEY: Ethtool.RETCODES[retcode]}
        else:
            return {ERROR_KEY: 'unhandled ethtool return code: %s' % retcode}

    def init_show_ring(self):
        errors = {
            re.compile(r".*No such device.*"): NoSuchDevice,
            re.compile(r".*Operation not permitted.*"): NotAllowed,
            re.compile(r".*[sudo] password for ufwi_rpcd:.*"): NotAllowed
                }

        struct = OutputStructure(r"Ring parameters for", errors=errors)

        default = OutputStructure("Pre-set maximums:")
        current = OutputStructure("Current hardware settings:")

        for section in (default, current):
            section.addField('rx', 'RX:\s*(.+)')
            section.addField('rx_mini', 'RX Mini:\s*(.+)')
            section.addField('rx_jumbo', 'RX Jumbo:\s*(.+)')
            section.addField('tx', 'TX:\s*(.+)')

        struct.sections = frozenset((('default', default), ('current', current)))

        cmd = "%(ethtool)s --show-ring %(iface)s" % ({
            'ethtool': self.ethtool_exe,
            'iface': "%%arg%%"
            })

        return Parser(struct, cmd, self, cmd_timeout=ETHTOOL_TIMEOUT)

    def ethtool_show_ring(self, iface_name):
        return self.show_ring.fetch(iface_name)

    def init_statistics(self):
        errors = {
            re.compile(r".*No such device.*"): NoSuchDevice,
            re.compile(r".*Operation not permitted.*"): NotAllowed,
            re.compile(r".*\[sudo\] password for ufwi_rpcd:.*"): NotAllowed
                }

        struct = OutputStructure(r"NIC statistics:", errors=errors)

        for line in (
"alloc_rx_buff_failed:"
"collisions:"
"dropped_smbus:"
"multicast:"
"rx_align_errors:"
"rx_broadcast:"
"rx_bytes:"
"rx_crc_errors:"
"rx_csum_offload_errors:"
"rx_csum_offload_good:"
"rx_dma_failed:"
"rx_drop_frame:"
"rx_dropped:"
"rx_errors:"
"rx_errors_total:"
"rx_extra_byte:"
"rx_fifo_errors:"
"rx_flow_control_pause:"
"rx_flow_control_unsupported:"
"rx_flow_control_xoff:"
"rx_flow_control_xon:"
"rx_frame_align_error:"
"rx_frame_error:"
"rx_frame_errors:"
"rx_frame_too_long:"
"rx_header_split:"
"rx_late_collision:"
"rx_length_error:"
"rx_length_errors:"
"rx_long_byte_count:"
"rx_long_length_errors:"
"rx_missed_errors:"
"rx_multicast:"
"rx_no_buffer_count:"
"rx_over_errors:"
"rx_packets:"
"rx_pause:"
"rx_runt:"
"rx_short_length_errors:"
"rx_smbus:"
"rx_tco_packets:"
"rx_unicast:"
"tx_aborted_errors:"
"tx_abort_late_coll:"
"tx_broadcast:"
"tx_bytes:"
"tx_carrier_errors:"
"tx_deferral:"
"tx_deferred:"
"tx_deferred_ok:"
"tx_dma_failed:"
"tx_dropped:"
"tx_errors:"
"tx_errors_total:"
"tx_excess_deferral:"
"tx_fifo_errors:"
"tx_flow_control_pause:"
"tx_flow_control_xoff:"
"tx_flow_control_xon:"
"tx_heartbeat_errors:"
"tx_late_collision:"
"tx_many_rexmt:"
"tx_multicast:"
"tx_multi_coll_ok:"
"tx_one_rexmt:"
"tx_packets:"
"tx_pause:"
"tx_restart_queue:"
"tx_retry_error:"
"tx_single_coll_ok:"
"tx_smbus:"
"tx_tco_packets:"
"tx_tcp_seg_failed:"
"tx_tcp_seg_good:"
"tx_timeout_count:"
"tx_window_errors:"
"tx_zero_rexmt:"
):
            field_name = line.strip()[:-1]
            regex = line.strip() + '\s*(.*)'
            struct.addField(field_name, regex)

        cmd = "%(ethtool)s --statistics %(iface)s" % ({
            'ethtool': self.ethtool_exe,
            'iface': "%%arg%%"
            })

        return Parser(struct, cmd, self, cmd_timeout=ETHTOOL_TIMEOUT)

    def ethtool_statistics(self, iface_name):
        return self.statistics.fetch(iface_name)

    def init_nooptions(self):
#Settings for eth0:
#        Supported ports: [ MII ]
#        Supported link modes:   10baseT/Half 10baseT/Full
#                                100baseT/Half 100baseT/Full
#        Supports auto-negotiation: Yes
#        Advertised link modes:  10baseT/Half 10baseT/Full
#                                100baseT/Half 100baseT/Full
#        Advertised auto-negotiation: Yes
#        Speed: 100Mb/s
#        Duplex: Full
#        Port: MII
#        PHYAD: 1
#        Transceiver: external
#        Auto-negotiation: on
#        Supports Wake-on: g
#        Wake-on: d
#        Link detected: yes

        errors = {
            re.compile(r".*No such device.*"): NoSuchDevice,
            re.compile(r".*Operation not permitted.*"): NotAllowed,
            re.compile(r".*\[sudo\] password for ufwi_rpcd:.*"): NotAllowed
                }
        struct = OutputStructure(r"Settings for [a-zA-Z]+[0-9]+:", errors=errors)

        fields = (
            "Supported ports:",
            "Supports auto-negotiation:",
            "Advertised auto-negotiation:",
            "Link partner advertised pause frame use:",
            "Link partner advertised auto-negotiation:",
            "Speed:",
            "Duplex:",
            "Port:",
            "PHYAD:",
            "Transceiver:",
            "Auto-negotiation:",
            "Supports Wake-on:",
            "Current message level:",
            "Wake-on:",
            "Link detected:"
        )

        for line in fields:
            field_name = line.strip()[:-1]
            regex = line.strip() + '\s*(.+)'
            struct.addField(field_name, regex)

        multiline_fields = (
            "Supported link modes:", #n lines!
            "Advertised link modes:", #n lines!
            "Link partner advertised link modes:",
        )

        for line in multiline_fields:
            field_name = line.strip()[:-1]
            regex = line.strip() + '\s*(.*)'
            struct.addField(field_name, regex, multiline=True)

        cmd = "%(ethtool)s %(iface)s" % ({
            'ethtool': self.ethtool_exe,
            'iface': "%%arg%%"
            })

        return Parser(struct, cmd, self, cmd_timeout=ETHTOOL_TIMEOUT)

    def ethtool_nooptions(self, iface_name):
        return self.nooptions.fetch(iface_name)
