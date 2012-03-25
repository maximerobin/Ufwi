#coding: utf-8
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

from ufwi_rpcd.common import EDENWALL
from ufwi_rpcd.common import tr
from ufwi_conf.common.dhcp_exceptions import DHCPError
from ufwi_conf.common.dhcp_exceptions import MissingData
from ufwi_conf.common.dhcp_exceptions import DHCPRangeNotInNet
from ufwi_conf.common.dhcp_exceptions import RouterNotInNet
from ufwi_conf.common.dhcp_exceptions import StartIPNotInNet
from ufwi_conf.common.dhcp_exceptions import EndIpNotInNet
from ufwi_conf.common.net_exceptions import NoMatch
from IPy import IP

_DHCPRANGE_STRING_ATTRS = (
    'router',
    'dns_server',
    'start',
    'end',
    )

UNSET = "____UNSET____"

DISABLED, ENABLED = False, True

class DHCPRange(object):
    """
    Transparently provides many services, such as finding out which IPs
    our server has on the served network :
    'net' refers to a netcfg net object, so that net.ip_addrs gives this information
    """
    def __init__(self, router, dns_server, start, end, net):
        """
        UNSET or None input is accepted, but unserializable.
        """
        self.router = self._ipOrUnset(router)
        self.dns_server = self._ipOrUnset(dns_server)
        self.start = self._ipOrUnset(start)
        self.end = self._ipOrUnset(end)

        self.net = net

    def _ipOrUnset(self, ip_or_none_or_unset):
        return \
            UNSET if self.isUnset(ip_or_none_or_unset) \
            else IP(ip_or_none_or_unset)

    def getRouterFromNet(self):
        """
        max raises ValueError: NO address on this net
        raises AttributeError: net is UNSET

        #TODO: This heuristic is (c) regit if any question.
        -usually, admins set the gateway as .254 or .127 (max in the range)
        """
        if self.net.service_ip_addrs:
            return unicode(max(self.net.service_ip_addrs))

        raise DHCPError(tr("Invalid router IP: there is no service IP on "
            "this network and you did not specify a router."))

    def isValid(self):
        if not isinstance(self.start, IP):
            if self.start in (UNSET, None, ""):
                raise MissingData(tr("Start IP is unset."))
        try:
            ip_start = IP(self.start)
        except:
            raise DHCPError(tr("Invalid start IP."))

        if not isinstance(self.end, IP):
            if self.end in (UNSET, None, ""):
                raise MissingData(tr("End IP is unset."))

        try:
            ip_end = IP(self.end)
        except:
            raise DHCPError(tr("Invalid end IP"))

        if ip_start.version == 6:
            raise DHCPError(tr("Start IP must be an IPv4 address."))

        if ip_end.version == 6:
            raise DHCPError(tr("End IP must be an IPv4 address."))

        if self.net is None:
            # possible if HA enabled with all interfaces without
            # primary/secondary IPs
            if EDENWALL:
                msg = tr("A network must be selected. If High Availability is "
                    "enabled you should add primary and secondary addresses.")
            else:
                msg = tr("A network must be selected.")
            raise DHCPError(msg)

        if not self.net.net.overlaps(ip_start):
            raise DHCPError(tr("Start IP is not in selected network."))

        if not self.net.net.overlaps(ip_end):
            raise DHCPError(tr("End IP is not in selected network."))

        if self.start == self.end:
            raise DHCPError(tr("Start and End IPs must be different."))

        if ip_end < ip_start:
            raise DHCPError(tr("Start IP should be smaller than end IP"))

        if self.router is not UNSET:
            try:
                ip_router = IP(self.router)
            except:
                raise DHCPError(tr("Invalid router IP"))
        else:
            ip_router = IP(self.getRouterFromNet())

        if self.dns_server is not UNSET:
            if self.isUnset(self.dns_server):
                # TODO should be allowed
                raise MissingData(tr("DNS IP should be specified"))

            try:
                IP(self.dns_server)
            except:
                raise DHCPError(tr("Invalid DNS IP"))

        ips = {
            ip_start: StartIPNotInNet,
            ip_end: EndIpNotInNet,
            ip_router: RouterNotInNet
            }
        for ip, exception in ips.iteritems():
            if not self.net.net.overlaps(ip):
                raise exception(ip)

        return True
    def is_fully_unset(self):
        return all(
            (self.isUnset(item) for item in (self.start, self.end, self.router))
            )

    def serialize(self):
        serialized = {}
        for attr in _DHCPRANGE_STRING_ATTRS:
            value = getattr(self, attr)
            if isinstance(value, IP):
                value = unicode(value)
            serialized[attr] = value

        if self.net is None:
            net_label = UNSET
        else:
            net_label = self.net.label
        serialized['net_label'] = net_label
        serialized['net_unique_id'] = self.net.unique_id
        return serialized

    def setRouter(self, value):
        self.router = self.ip_or_unset(value)

    def setDns(self, value):
        self.dns_server = self.ip_or_unset(value)

    def setStart(self, value):
        self.start = self.ip_or_unset(value)

    def setEnd(self, value):
        self.end = self.ip_or_unset(value)

    def getRouterText(self):
        return self._IP2text(self.router)

    def getDnsText(self):
        return self._IP2text(self.dns_server)

    def getStartText(self):
        return self._IP2text(self.start)

    def getEndText(self):
        return self._IP2text(self.end)

    @classmethod
    def _IP2text(cls, value):
        if cls.isUnset(value):
            return ''
        return unicode(value)

    @classmethod
    def ip_or_unset(cls, value):
        """
        supply anything that looks like data and we'll try and set something correct
        """
        if cls.isUnset(value):
            return UNSET
        try:
            return IP(value)
        except ValueError:
            return value

    @classmethod
    def isUnset(cls, value):
        if isinstance(value, IP):
            return False
        return value in (UNSET, None, '')

def deserializeRange(serialized, netcfg):
    if not isinstance(serialized, dict):
        raise DHCPError("Invalid serialized range")
    args = [serialized[attr] for attr in _DHCPRANGE_STRING_ATTRS]
    args = [arg if arg != UNSET else UNSET for arg in args]
    #If NoMatch here: incoherence between netcfg and dhcp
    try:
        args.append(netcfg.getNetByUniqueID(serialized['net_unique_id']))
    except NoMatch, err:
        raise err
    else:
        deserialized = DHCPRange(*args)

    return deserialized

class DHCPCfg(object):
    def __init__(self, ranges=None, enabled=DISABLED):
        if ranges is None:
            ranges = set()
        self.ranges = ranges
        self.enabled = enabled

    def serialize(self):
        serialized = {}
        serialized['enabled'] = self.enabled

        ranges_repr = {}
        RANGE_KEY_PREFIX = 'range'
        for index, range in enumerate(self.ranges):
            key = "%s %s" % (RANGE_KEY_PREFIX, index)
            ranges_repr[key] = range.serialize()

        serialized['ranges'] = ranges_repr

        return serialized

    def isValid(self):
        ok, msg = self.isValidWithMsg()
        return ok

    def isValidWithMsg(self):
        #if not self.enabled:
        #    return True
        for dhcprange in self.ranges:
            try:
                dhcprange.isValid()
            except DHCPError, err:
                if err.args:
                    return False, "invalid range: %s - %s" % (str(dhcprange), err.args[0])
                else:
                    return False, "invalid range: %s" % str(dhcprange)
        return True, "Valid configuration"

    def computeChanges(self, netcfg):
        deletable = set()
        translatable = set()

        for range in self.ranges:
            try:
                netcfg.getNetByUniqueID(range.net.unique_id)
            except NoMatch:
                deletable.add(range)
                continue
            try:
                range.isValid()
            except DHCPRangeNotInNet:
                translatable.add(range)
            except MissingData:
                #This range is invalid because it is
                #incomplete, don't bother about it
                pass
            except DHCPError, err:
                raise err
                #Actually this is unexpected.

        return deletable, translatable


def deserialize(serialized, netcfg):
    ranges = set()
    if serialized.has_key('ranges'):
        for range_repr in serialized['ranges'].values():
            try:
                range = deserializeRange(range_repr, netcfg)
            except NoMatch:
                print "Cannot deserialize a range. Not fatal, but annoying"
            else:
                ranges.add(range)
    enabled = serialized['enabled']
    return DHCPCfg(ranges, enabled)
