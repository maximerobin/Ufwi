# -*- coding: utf-8 -*-

"""
Copyright (C) 2008-2011 EdenWall Technologies
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

from PyQt4.QtGui import QWidget
from PyQt4.QtCore import QRegExp

from ufwi_log.client.qt.args.argfilter import *
from ufwi_log.client.qt.args.argdata import *
from ufwi_log.client.qt.fragtypes import frag_types
from ufwi_rpcd.common import tr
from ufwi_rpcd.common.odict import odict

from copy import copy

IP_REG = '^[\d]{2,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}$'

class ArgType:
    """ Class to give informations of an argument type """

    def __init__(self, label='', filterClass=None, dataClass=None, links=[], pagelinks=[], pagelink_args=None, unit=''):
        """
            @param label [string] this is the label of this arg
            @param filterClass [ArgFilterBas] a class derived from ArgFilterBase
            @param dataClass [ArgDataBase] a class derived from ArgDataBase
            @param links [list] list of arguments linked to this (must be strings)
            @param pagelinks [list[str]] pages linked to this argument
            @param pagelink_args [dict] arguments given to new page
        """
        self.label = label
        self.filterClass = filterClass
        self.dataClass = dataClass
        self.links = copy(links)
        self.pagelinks = copy(pagelinks)
        self.pagelink_args = copy(pagelink_args)
        self.unit = unit

    def filter(self, *args, **kwargs):
        if self.filterClass:
            return self.filterClass(*args, **kwargs)
        else:
            return ArgFilterForbidden(*args, **kwargs)

    def data(self, *args, **kwargs):
        if self.dataClass:
            return self.dataClass(*args, **kwargs)
        else:
            return ArgDataBase(*args, **kwargs)

    def get_pagelink_args(self, arg, data):
        args = {}

        try:
            templ_args = self.pagelink_args
            for key, val in templ_args.items():
                if val == ArgDataBase.VALUE:
                    val = data.value
                elif val == ArgDataBase.LABEL:
                    val = data.label
                args[key] = val
        except (KeyError, AttributeError):
            args[arg] = data.value

        return args

    def get_pagelink_default(self, field, arg_data):
        try:
            return self.pagelinks[0]
        except IndexError:
            return None

    def get_pagelinks(self, field, arg_data):
        return self.pagelinks

    def add_pagelink(self, pagename):
        self.pagelinks.append(pagename)

class ArgSourceType(ArgType):
    def filter(self, client, arg, value, *args, **kwargs):
        ip_reg = QRegExp(IP_REG)
        if isinstance(value, list) or isinstance(value, tuple) or isinstance(value, str) or isinstance(value, int) or not ip_reg.exactMatch(value):
            return ArgFilterUserID(client, arg, value, *args, **kwargs)
        else:
            return ArgFilterIP(client, arg, value, *args, **kwargs)


    def data(self, arg, value, *args, **kwargs):
        ip_reg = QRegExp(IP_REG)
        if (isinstance(value, list) or isinstance(value, tuple) or isinstance(value, str) or isinstance(value, int)) \
                and not ip_reg.exactMatch(str(value)):
            return ArgDataUserID(arg, value, *args, **kwargs)
        else:
            return ArgDataIP(arg, value, *args, **kwargs)

    def get_pagelink_args(self, field, arg_data):
        if isinstance(arg_data.value, int) and not arg_data.compatibility.user_id:
            value = arg_data.label
        else:
            value = arg_data.value
        ip_reg = QRegExp(IP_REG)
        if (isinstance(value, list) or isinstance(value, tuple) or isinstance(value, str) or isinstance(value, int)) \
                and not ip_reg.exactMatch(str(value)):
            return arg_types['username'].get_pagelink_args(field, arg_data)
        else:
            return arg_types['ip_saddr_str'].get_pagelink_args(field, arg_data)

    def get_pagelink_default(self, field, arg_data):
        if isinstance(arg_data.value, int) and not arg_data.compatibility.user_id:
            value = arg_data.label
        else:
            value = arg_data.value
        ip_reg = QRegExp(IP_REG)
        if (isinstance(value, list) or isinstance(value, tuple) or isinstance(value, str) or isinstance(value, int)) \
                and not ip_reg.exactMatch(str(value)):
            return arg_types['username'].get_pagelink_default(field, arg_data)
        else:
            return arg_types['ip_saddr_str'].get_pagelink_default(field, arg_data)

    def get_pagelinks(self, field, arg_data):
        if isinstance(arg_data.value, int) and not arg_data.compatibility.user_id:
            value = arg_data.label
        else:
            value = arg_data.value
        ip_reg = QRegExp(IP_REG)
        if (isinstance(value, list) or isinstance(value, tuple) or isinstance(value, str) or isinstance(value, int)) \
                and not ip_reg.exactMatch(str(value)):
            return arg_types['username'].get_pagelinks(field, arg_data)
        else:
            return arg_types['ip_saddr_str'].get_pagelinks(field, arg_data)

arg_types = {
    '_id':           ArgType(tr('ID'), ArgFilterInt, None),
    'packet_id':    ArgType(tr('         '), ArgFilterInt, ArgDataAuthenticated),
    'authenticated':ArgType(tr('         '), None, ArgDataAuthenticated),
    'tcp_dport':    ArgType(tr('TCP dest port'), ArgFilterPort, ArgDataPort, pagelink_args={'dport': ArgDataBase.VALUE, 'proto': 'tcp'}),
    'tcp_sport':    ArgType(tr('TCP source port'), ArgFilterPort, ArgDataPort, pagelink_args={'sport': ArgDataBase.VALUE, 'proto': 'tcp'}),
    'udp_dport':    ArgType(tr('UDP dest port'), ArgFilterPort, ArgDataPort, pagelink_args={'dport': ArgDataBase.VALUE, 'proto': 'udp'}),
    'udp_sport':    ArgType(tr('UDP source port'), ArgFilterPort, ArgDataPort, pagelink_args={'sport': ArgDataBase.VALUE, 'proto': 'udp'}),
    'sport':        ArgType(tr('Sport'), ArgFilterPort, ArgDataPort),
    'dport':        ArgType(tr('Dport'), ArgFilterPort, ArgDataPort),
    'source':       ArgSourceType(tr('Source'), ArgFilterIP, ArgDataIP),
    'ip_saddr_str':     ArgType(tr('Source'), ArgFilterIP, ArgDataIP, pagelink_args={'ip_saddr_str': ArgDataBase.VALUE}),
    'ip_daddr_str':     ArgType(tr('Destination'), ArgFilterIP, ArgDataIP),
    'ip_addr':      ArgType(tr('Address'), ArgFilterIP, ArgDataIP),
    'ip_from':      ArgType(),
    'orig_ipv6_src':ArgType(tr('Orig source'), ArgFilterIntIP, ArgDataIPv6),
    'orig_ipv6_dst':ArgType(tr('Orig dest.'), ArgFilterIntIP, ArgDataIPv6),
    'orig_ipv4_src':ArgType(tr('Orig source'), ArgFilterIntIP, ArgDataIPv4),
    'orig_ipv4_dst':ArgType(tr('Orig dest.'), ArgFilterIntIP, ArgDataIPv4),
    'orig_port_src':ArgType(tr('Orig Sport'), ArgFilterPort, ArgDataPort),
    'orig_port_dst':ArgType(tr('Orig Dport'), ArgFilterPort, ArgDataPort),
    'repl_ipv6_src':ArgType(tr('Reply source'), ArgFilterIntIP, ArgDataIPv6),
    'repl_ipv6_dst':ArgType(tr('Reply dest.'), ArgFilterIntIP, ArgDataIPv6),
    'repl_ipv4_src':ArgType(tr('Reply source'), ArgFilterIntIP, ArgDataIPv4),
    'repl_ipv4_dst':ArgType(tr('Reply dest.'), ArgFilterIntIP, ArgDataIPv4),
    'repl_port_src':ArgType(tr('Rep Sport'), ArgFilterPort, ArgDataPort),
    'repl_port_dst':ArgType(tr('Rep Dport'), ArgFilterPort, ArgDataPort),
    'reason':   ArgType(tr('Reason'), ArgFilterText, ArgDataApp),
#    'username':     ArgType(tr('User'),            None,               ArgDataUser,           pagelink_args={'user_id': ArgDataBase.VALUE}),
    'username':     ArgType(tr('User'), ArgFilterUserID, ArgDataUserID, pagelink_args={'username': ArgDataBase.VALUE}),
    'user_id':      ArgType(tr('User'), ArgFilterUserID, ArgDataUserID, pagelink_args={'user_id': ArgDataBase.VALUE}),
    'usergroup':     ArgType(tr('User Group'), None, ArgDataUser),
    'userlike':     ArgType(tr('Username contains'), ArgFilterText),
    'raw_label':        ArgType(tr('State'), ArgFilterState, ArgDataState),
    'proto':        ArgType(tr('Protocol'), ArgFilterProto),
    'limit':        ArgType('', ArgFilterForbidden),
    'start':        ArgType('', ArgFilterForbidden),
    'sort':         ArgType('', ArgFilterForbidden),
    'sortby':       ArgType('', ArgFilterForbidden),
    'packets':      ArgType(tr('Packets'), ArgFilterForbidden, unit=tr("packets")),
    'start_time':   ArgType(tr('First packet'), ArgFilterTimestamp, ArgDataTimestamp),
    'end_time':     ArgType(tr('Last packet'), ArgFilterTimestamp, ArgDataTimestamp),
    'session_start_time':   ArgType(tr('Session start'), ArgFilterDatetime, ArgDataTimestamp),
    'session_end_time':   ArgType(tr('Session end'), ArgFilterDatetime, ArgDataTimestamp),
    'expire':       ArgType(tr('Expire'), ArgFilterTimestamp, ArgDataTimestamp),
    'oob_time_sec': ArgType(tr('Time'), None, ArgDataTimestamp),
    'time':         ArgType(tr('Time'), None, ArgDataTimestamp),
    'currents':     ArgType('', ArgFilterForbidden), # deprecated?
    'client_app':   ArgType(tr('Application'), ArgFilterText, ArgDataApp),
    'firewall':     ArgType(tr('Firewall'), ArgFilterFirewall),
    'tiny':         ArgType('', ArgFilterForbidden),
    'oob_prefix':   ArgType(tr('Prefix'), ArgFilterText),
    'acl':          ArgType(tr('Filtering Rule'), ArgFilterInt, ArgDataAcl),
    'os_sysname':   ArgType(tr('System')),
    'mark':         ArgType(tr('Mark')),
    'timeout':      ArgType(tr('Timeout')),
    'status':       ArgType(tr('Status')),
    'groups':       ArgType(tr('Groups'), None, ArgDataUserGroups),
    'client_version':ArgType(tr('Client version')),
    'bytes_in':     ArgType(tr('Bytes In'), ArgFilterForbidden, ArgDataBytes, unit=tr("bytes")),
    'bytes_out':    ArgType(tr('Bytes Out'), ArgFilterForbidden, ArgDataBytes, unit=tr("bytes")),
    'memory_used':  ArgType(tr('Memory in use'), ArgFilterForbidden, ArgDataBytes, unit=tr("bytes")),
    'memory_total': ArgType(tr('Total memory'), ArgFilterForbidden, ArgDataBytes, unit=tr("bytes")),

    'kill':         ArgType(tr('Action'), None, ArgDataKill),
    'hostname':     ArgType(tr('Hostname'), ArgFilterText),
    'workgroup':    ArgType(tr('Workgroup'), ArgFilterText),
    'interface':    ArgType(tr('Interface'), ArgFilterText),
    'ocs_id':       ArgType(tr('OCS Id'), ArgFilterInt),
    'interval':     ArgType(tr('Interval'), ArgFilterInt, unit=tr('seconds')),
    'load1':        ArgType(tr('Load (1 min)'), None),
    'load5':        ArgType(tr('Load (5 min)'), None),
    'load15':       ArgType(tr('Load (15 min)'), None),
    'method':       ArgType(tr('Method'), ArgFilterText),
    'url':          ArgType(tr('URL'), ArgFilterText),
    'domain':       ArgType(tr('Domain'), ArgFilterText),
    'proxy_username':ArgType(tr('Username'), ArgFilterText),
    'proxy_state':  ArgType(tr('State'), ArgFilterText),
    'request_id':   ArgType(tr('ID'), ArgFilterInt),
    'requests':     ArgType(tr('Requests'), ArgFilterForbidden, unit=tr("requests")),
    'volume':       ArgType(tr('Volume'), ArgFilterForbidden, ArgDataBytes, unit=tr("bytes")),
}

class Args:
    """ This class can be used to analyze arguments... """

    def __init__(self, args={}, fetcher=None):
        self.args = args
        self.fetcher = fetcher

    def no_filters(self):

        new_args = dict()
        for key, value in self.args.items():
            if arg_types.has_key(key) and not arg_types[key].filterClass:
                new_args[key] = value

        return new_args

    def filters(self):

        new_args = dict()
        for key, value in self.args.items():
            if arg_types.has_key(key) and arg_types[key].filterClass:
                new_args[key] = value

        return new_args

    def remove(self, key):

        d = {key: None}

        try:
            for k in arg_types[key].links:
                d[k] = None
        except:
            pass

        return d

    ###################
    #      LABELS     #
    ###################

    def sort_label(self):
        """ With my args, get a label to say on what field my list is ordered. """

        if not self.args.has_key('sortby') or not arg_types.has_key(self.args['sortby']):
            return tr('No sorting')

        return tr(u'Sorted by %s') % (arg_types[self.args['sortby']].label)

    def labels_dict(self):
        labels = dict()

        for key, value in self.args.items():
            arg_data = arg_types[key].data(key, value, self.fetcher)

            if arg_data.label and not isinstance(arg_data.label, QWidget):
                label = unicode(arg_data.label)
            else:
                label = unicode(value)

            labels[key] = u'%s %s' % (arg_types[key].label, label)
            if arg_types[key].unit:
                labels[key] += arg_types[key].unit

        return labels

    def labels(self, fragtype=''):
        """ Get a label to show on what criteria this list is built. """

        label = ''
        labels = self.labels_dict()

        for value in labels.values():

            if label:
                label += ', '
            label += value

        # If a fragtype is given, we use the label associated.
        if fragtype and frag_types.has_key(fragtype):
            if label:
                label = '%s %s %s' % (tr(frag_types[fragtype].title), tr('for'), label)
            else:
                label = tr(frag_types[fragtype].title)

        return label

class Interval:

    mode_list = odict()
    mode_list['hourly'] = tr('1 hour range')
    mode_list['daily'] = tr('24 hours range')
    mode_list['weekly'] = tr('7 days range')
    mode_list['monthly'] = tr('31 days range')
    mode_list['custom'] = tr('Custom range')
    mode_list['search'] = tr('Search mode')

    MONTH = 31 * 24 * 3600

    def __init__(self, mode, start=None, end=None):
        if not self.mode_list.has_key(str(mode)):
            return
        self.server_time = None
        self.mode = mode
        if mode == 'custom':
            if start:
                self.start = start
            if end:
                self.end = end
        self.last_start_time = None
        self.last_end_time = None

    def display(self):
        if self.getMode() == 'custom':
            return '%s-%s' % (self.getStart().toString(), self.getEnd().toString())
        return self.mode_list[str(self.getMode())]

    def getMode(self):
        return self.mode

    def setGUI(self, updateinterval):
        for key, value in self.mode_list.items():
            if (key != 'search'):
                updateinterval.addItem(value, QVariant(key))

    def setStart(self, datet):
#        if self.getMode() == 'custom':
        self.start = datet

    def setServerTime(self, datet):
        self.server_time = QDateTime.fromTime_t(datet)

    def getStart(self):
        if self.getMode() == 'hourly':
            datet = self.server_time.addSecs(-3600)
        if self.getMode() == 'daily':
            datet = self.server_time.addDays(-1)
        if self.getMode() == 'weekly':
            datet = self.server_time.addDays(-7)
        if self.getMode() == 'monthly':
            datet = self.server_time.addDays(-31)
        if self.getMode() == 'custom':
            return self.start
        return datet

    def getStartClient(self):
        if not self.last_start_time:
            return QDateTime.fromTime_t(QDateTime.currentDateTime().toTime_t() - self.MONTH)
        else:
            return QDateTime.fromTime_t(self.last_start_time)

    def getEndClient(self):
        if not self.last_end_time:
            return QDateTime.currentDateTime()
        else:
            return QDateTime.fromTime_t(self.last_end_time)

    def setLastEndClient(self, last_end_time):
        self.last_end_time = last_end_time

    def setLastStartTime(self, last_start_time):
        self.last_start_time = last_start_time

    def delta(self):
        return QDateTime.currentDateTime().toTime_t() - self.server_time.toTime_t()

    def setEnd(self, datet):
        self.end = datet

    def getEnd(self):
        if self.getMode() != 'custom':
            return self.server_time
        else:
            return self.end

