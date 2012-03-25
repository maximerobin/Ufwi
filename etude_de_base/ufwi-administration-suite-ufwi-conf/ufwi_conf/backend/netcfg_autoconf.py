
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

from subprocess import Popen, PIPE
from ufwi_rpcd.backend.logger import Logger
import re
import IPy

from ufwi_rpcd.common.error import exceptionAsUnicode, reraise
from ufwi_conf.common.netcfg_rw import NetCfgRW as NetCfg
from ufwi_conf.common.net_exceptions import ParseError, NuconfException, NoMatch, NetCfgError
from ufwi_conf.common.net_interfaces import Bonding
from ufwi_conf.common.net_interfaces import Ethernet
from ufwi_conf.common.net_interfaces import PointToPoint
from ufwi_conf.common.net_interfaces import Vlan
from ufwi_conf.common.net_objects_rw import NetRW
from ufwi_conf.common.net_objects_rw import RouteRW

LOCAL_IFACES = ('lo',)
LOCAL_SCOPES = ('link', 'site', 'host')

IGNORED_INTERFACE = "__IGNORED_INTERFACE__"

class IgnoredData(NuconfException):
    def __init__(self, wait = None, msg = ''):
        Exception.__init__(self, msg)
        self.wait = wait

class NetCfgAutoConf(NetCfg, Logger):
    #Commands used here
    IP_NET_CMD = '/sbin/ip addr list'
    IP_ROUTE_CMD = '/sbin/ip route list'
    IP_ROUTE6_CMD = '/sbin/ip -6 route list'

    #Ids for the lines found in above commands
    IFACEHW, \
    IF_LOOPBACK, \
    IF_POINTTOPOINT, \
    IF_ETHERNET, \
    IF_BONDING, \
    IF_VLAN, \
    IF_BRIDGE, \
    IF_WLAN, \
    IF_EW4MASTER, \
    IF_TAP, \
    IF_TUN, \
    IF_OTHER_IGNORED, \
    IP, \
    IP_PROP = ( 1 << x for x in range(14))

    IFACE = IF_LOOPBACK | IF_POINTTOPOINT | IF_ETHERNET | IF_BONDING | IF_VLAN | IF_BRIDGE | IF_WLAN | IF_EW4MASTER | IF_TAP | IF_TUN
    IGNORED_IFACES = IF_LOOPBACK | IF_OTHER_IGNORED

    def __init__(self, parent=None, ethernets=None, vlans=None, bondings=None):
        Logger.__init__(self, 'netcfg', parent=parent)
        NetCfg.__init__(self, ethernets, vlans, bondings)

        self.discovering = False

        interface_number_regex = r"(\A[0-9]+: )"

        #bond0:  mtu 1500 qdisc noqueue
        self.loopback_regex = re.compile(interface_number_regex + r"(lo):*")
        #51: ew4master0: <POINTOPOINT,MULTICAST,NOARP,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UNKNOWN qlen 100
        self.pointtopoint_regex = re.compile(interface_number_regex + r"(.+): <.*POINTOPOINT.*>(.*)")
        self.ethernet_regex, \
        self.bonding_regex, \
        self.vlan_regex, \
        self.wlan, \
        self.ew4master, \
        self.tap, \
        self.tun, \
        self.bridge = (
            re.compile(
                interface_number_regex + r'(%s[0-9]+): <(.*)>(.*)' % iftype
                )
            for iftype in 'eth bond vlan wlan ew4master tap tun br'.split()
        )
        self.other_interfaces = re.compile(
                interface_number_regex + r'(\w+): <(.*)>(.*)'
                )

        hexa = r'[0-9a-fA-F]'
        column_addr = r'(?:%s{2}:)+%s{2}' % (hexa, hexa)
        self.iface_hw_regex = re.compile(r'.*(link/)(.+)')

        protocols = r'inet(?:6){0,1}'
        mask = r'[0-9]{1,3}'

        peer = r"""
        (?:
            \s peer \s       # keyword
            (?:.+)           # peer address
        )
        """

        addr_begin = r"""
        (%s) \s            # protocol: inet|inet6 (retained)
        (.+)               # ip address
        """ % (protocols)

        addr_mid = r"""
        /                  # mask separation char
        (%s)               # mask
        \s
        (?:brd (.+) \s )   # broadcast addr...
        {0,1}              #... is optional
        scope \s (\w+)     # scope: retained
        \s{0,1}(\w*)       # optional end (retained)
        """ % (mask)

        self.pppip_addr_def_regex = re.compile(
        r"""
        %s                 # addr_begin
        %s                 # peer option regex
        %s                 # addr_mid
        """ % (addr_begin, peer, addr_mid),
        re.VERBOSE
        )

        self.ip_addr_def_regex = re.compile(
        r"""
        %s
        %s
        """ % (addr_begin, addr_mid),
        re.VERBOSE
        )

        #Be careful to match secondnet before net
        self.secondip_addr_def_regex = re.compile(
        r"""
        %s
        /(%s) \s (?:brd (.+) \s ){0,1}scope \s (\w+) \s secondary\s{0,1}(\w*)
        """ % (addr_begin, mask),
        re.VERBOSE
        )

        self.ipv6_props = re.compile(r'valid_lft')

    def _addInterface(self, interface):
        if isinstance(interface, Ethernet):
            self.ethernets.add(interface)
        elif isinstance(interface, Vlan):
            self.vlans.add(interface)
        elif isinstance(interface, Bonding):
            self.bondings.add(interface)
        elif isinstance(interface, PointToPoint):
            self.pointtopoints.add(interface)
        else:
            #Programming error: should fall in above cases
            assert False, "Unexpected interface type: %s" % type(interface)

    def discover(self, ip_flow=None, route_flow=None, route6_flow=None):
        """
        ip_flow, route_flow: file descriptors for stdout of 'ip addr list' and 'ip route list'
        """
        added = set()
        ignored = set()
        self.important("Auto discovering network parameters")
        self.discovering = True
        if ip_flow == None:
            ip_flow = self.runCmd(NetCfgAutoConf.IP_NET_CMD)

        cur_iface = None
        wait = NetCfgAutoConf.IFACE
        for line in ip_flow:
            try:
                line_class, data = self.matchLineClass(line)
                if data is IGNORED_INTERFACE:
                    cur_iface = None
                    self.debug("Ignoring interface specified by <%s>" % line)
                    continue
            except IgnoredData, err:
                self.debug("ignored %s" % line)
                wait = err.wait
                continue
            except Exception, err:
                reraise(ParseError(u"Error on line %r: %s" % (line, exceptionAsUnicode(err))))
            if line_class is NetCfgAutoConf.IF_LOOPBACK:
                wait = NetCfgAutoConf.IFACEHW

            elif NetCfgAutoConf.IFACE & line_class:

                wait = NetCfgAutoConf.IFACEHW
                if NetCfgAutoConf.IGNORED_IFACES & line_class:
                    cur_iface = None
                    self.debug("dropping interface definition %s" % line)
                else:
                    self._addInterface(data)
                    cur_iface = data
                    added.add(data.system_name)
            elif wait in (None, NetCfgAutoConf.IFACEHW) and line_class == NetCfgAutoConf.IFACEHW:
                wait = None
            elif wait in (None, NetCfgAutoConf.IP) and line_class == NetCfgAutoConf.IP:
                if cur_iface is not None:
                    try:
                        cur_iface.addIP(data[0])
                    except NetCfgError:
                        net = IPy.IP(data[1], make_net = True)
                        label = "%s/%s" % (net.net(), net.prefixlen())
                        net = NetRW(label, net)
                        cur_iface.nets.add(net)
                        ip_addr = data[0]
                        if not cur_iface.addIP(ip_addr):
                            raise NuconfException('Problem in code')

                wait = None
            elif wait in (None, NetCfgAutoConf.IP_PROP) and line_class == NetCfgAutoConf.IP_PROP:
                wait = None

        self.important("Added %s" %  ", ".join(added))

        self.parseRoutes(route_flow, False)
        self.parseRoutes(route6_flow, True)

    def parseRoutes(self, route_flow, ipv6):
        if route_flow == None:
            if ipv6:
                arguments = NetCfgAutoConf.IP_ROUTE_CMD
            else:
                arguments = NetCfgAutoConf.IP_ROUTE6_CMD
            route_flow = self.runCmd(arguments)
        for line in route_flow:
            words = line.split()
            if words[1] == 'via':
                dst = words[0]
                router = words[2]
                dev = words[4]
                try:
                    iface = self.getIfaceByName(dev)
                    route = RouteRW(dst, router)
                    iface.routes.add(route)
                except NoMatch:
                    pass
            else:
                self.debug("Ignore route: %s" % line.rstrip())
        self.discovering = False

    def matchLineClass(self, line):
        def ignoreinterface(*args, **kwargs):
            return IGNORED_INTERFACE
        for regex, build_function, id in zip(
            #Order is important
            (
                #interfaces
                self.loopback_regex,
                self.pointtopoint_regex,
                self.ethernet_regex,
                #ignored
                self.bonding_regex,
                self.vlan_regex,
                self.wlan,
                self.ew4master,
                self.tap,
                self.tun,
                self.bridge,
                self.other_interfaces,
                #interface data
                self.iface_hw_regex,
            ),
            (
                #interfaces
                self.buildIfLoopback,
                self.buildIfPointToPoint,
                self.buildIfEthernet,
                #quickfix: ignore
                ignoreinterface,
                #self.buildIfBonding,
                self.buildIfVlan,
                #TODO: Should build wlan interface, not ethernet
                self.buildIfEthernet,
                #TODO: Should build ptp interface, not ethernet
                self.buildIfEthernet,
                self.buildIfPointToPoint,
                self.buildIfPointToPoint,
                self.buildIfEthernet,
                ignoreinterface,
                #interface data
                self.buildIfaceHw,
            ),
            (
                #interfaces
                NetCfgAutoConf.IF_LOOPBACK,
                NetCfgAutoConf.IF_POINTTOPOINT,
                NetCfgAutoConf.IF_ETHERNET,
                #quickfix: ignore
                NetCfgAutoConf.IF_OTHER_IGNORED,
                #NetCfgAutoConf.IF_BONDING,
                NetCfgAutoConf.IF_VLAN,
                NetCfgAutoConf.IF_WLAN,
                NetCfgAutoConf.IF_EW4MASTER,
                NetCfgAutoConf.IF_TAP,
                NetCfgAutoConf.IF_TUN,
                NetCfgAutoConf.IF_BRIDGE,
                NetCfgAutoConf.IF_OTHER_IGNORED,
                #interface data
                NetCfgAutoConf.IFACEHW,
            )
        ):
            data = regex.split(line)
            if len(data) != 1:
                return id, build_function(data)

        #Not factorized because of 'primary' argument:
        data = self.pppip_addr_def_regex.split(line)
        if len(data) != 1:
            return NetCfgAutoConf.IP, self.buildIPAddr(data, primary = True)
        data = self.secondip_addr_def_regex.split(line)
        if len(data) != 1:
            return NetCfgAutoConf.IP, self.buildIPAddr(data, primary = False)
        data = self.ip_addr_def_regex.split(line)
        if len(data) != 1:
            return NetCfgAutoConf.IP, self.buildIPAddr(data, primary = True)
        data = self.ipv6_props.split(line)
        if len(data) != 1:
            return NetCfgAutoConf.IP_PROP, line
        raise NoMatch('unparseable line: %s' % line)

    def buildIfLoopback(self, data):
        name = data[2]
        assert name in LOCAL_IFACES
        return None

    def buildIfEthernet(self, data):
        name = data[2]
        return Ethernet(system_name=name)

    def buildIfBonding(self, data):
        name = data[2]
        return Bonding(system_name=name)

    def buildIfVlan(self, data):
        name = data[2]
        return Vlan(system_name=name)

    def buildIfPointToPoint(self, data):
        name = data[2]
        return PointToPoint(system_name=name)

    def buildIfaceHw(self, data):
        #data = ['    ', 'ether', '00:16:41:59:f0:6b', 'ff:ff:ff:ff:ff:ff', '\n']
        return data[1]

    def buildIPAddr(self, data, primary = True):
        #data = ['    ', 'inet', '192.168.0.10', '24', '192.168.0.255', 'global', 'eth0', '\n']
        #data = ['    ', 'inet6', 'fe80::216:41ff:fe59:f06b', '64', None, 'link', '', '\n']
        scope = data[5]
        if scope in LOCAL_SCOPES:
            msg = "Discarding %s (scope local)" % data[2]
            self.debug(msg)
            raise IgnoredData(msg)
        addr = data[2]
        mask = data[3]
        dev = data[6]
        return IPy.IP(addr), "%s/%s" % (addr, mask)

    def runCmd(self, cmd_line):
        try:
            # FIXME: use createProcess + communicateProcess() with a timeout
            process = Popen(cmd_line.split(), stdout=PIPE, env={})
            for line in process.stdout:
                yield line.rstrip()
            process.wait()
        except OSError, err:
            self.error("Problem running '%s':\n%s", cmd_line, err)
            raise err


