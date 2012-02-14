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

import socket
from time import strftime, localtime
from datetime import datetime
from IPy import IP
import random

from PyQt4.QtGui import QAction, QLabel, QPixmap, QPushButton, QMessageBox, QIcon
from PyQt4.QtCore import SIGNAL, QTimer, QObject

from ufwi_rpcd.common import tr
from ufwi_rpcd.common.error import writeError
from ufwi_rpcd.common.tools import formatList

from ufwi_log.client.qt.info_area import InfoArea
from ufwi_log.client.qt.tools import createLink

DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
TIME_FORMAT = '%H:%M:%S'

class ArgDataBase(QObject):

    class VALUE: pass
    class LABEL: pass

    def __init__(self, arg, value, fetcher=None, compatibility=None, transform_label=True, parent=None):
        """
            This objet can be used to graphical representation of a value.

            @param arg [str]  the argument name
            @param value  the value can be a string, or a tuple of two strings
                          if there is a distinction between label (displayed)
                          and the value (used to link to others pages)
                          A function can be overloaded to get an other string
                          or a Qt widget from data.
            @param fetcher  this object is used to communicate with background
            @param transform_label [bool]  the label transformation is made only
                                           if this is true (default)
        """

        QObject.__init__(self, parent)

        self.arg = arg
        self.fetcher = fetcher
        self.compatibility = compatibility
#        if parent:
#            self.compatibility = parent.user_settings.compatibility

        self._fill_value(value)

        if transform_label and self.label != None:
            try:
                self.label = self._get_label()
            except Exception, err:
                writeError(err, "Error on getting argument label")

    def _fill_value(self, value):
        if isinstance(value, tuple) or isinstance(value, list):
            self.label = value[0]
            self.value = value[1]
        else:
            self.label = value
            self.value = value

    def _get_label(self):
        return self.label

    def actions(self):
        """ Returns a list of actions used in context menu """
        return []

class ArgDataAuthenticated(ArgDataBase):
    def _get_label(self):
        data = QLabel()
        data.setStyleSheet('padding-left: 2px; padding-right: 2px')
        if int(self.label):
            data.setPixmap(QPixmap(':/icons-20/one_user.png'))
        else:
            data.setPixmap(QPixmap(':/icons-20/one_screen.png'))

        return data

class ArgDataKill(ArgDataBase):
    def _get_label(self):
        try:
            icon = QIcon(':/icons/users_deconnection.png')
            widget = QPushButton(icon, '')
            if self.fetcher.canKill():
                widget.connect(widget, SIGNAL('clicked(bool)'), lambda b: ArgDataKill.kill(self.fetcher, self.value, widget))
            else:
                widget.setEnabled(False)
            return widget
        except AttributeError:
            return self.value

    @staticmethod
    def kill(fetcher, value, widget):
        try:
            fetcher.kill(value)
            widget.emit(SIGNAL('want_update'))
        except AttributeError:
            pass

class ArgDataUser(ArgDataBase):
    def _get_label(self):
        return self.label or 'N/A'

class ArgDataUserID(ArgDataBase):
    def _get_label(self):
        if self.fetcher:
            if self.compatibility.user_id:
                userlist = self.fetcher.client.call('ufwi_log', 'table', 'UserIDTable', {'user_id': int(self.value)})

                if len(userlist) > 0:
                    return userlist[0][0]
            else:
                return self.label

        return self.label

class ArgDataAcl(ArgDataBase):
    def _get_label(self):
        acl = self.label.split(' ')[0].split(':')

        if len(acl) != 3:
            return ''

        return createLink(':/icons-20/Acl.png', lambda: self.show_acl(acl), self.tr("Show filtering rule in the firewall"))

    def show_acl(self, acl):
        assert len(acl) == 3
        rules_list = acl[2]
        acl_id = int(acl[1])
        self.emit(SIGNAL('EAS_Message'), 'nufaceqt', 'show_acl', rules_list, acl_id)

class ArgDataIP(ArgDataBase):

    DNS_CACHE = {}

    def __init__(self, arg, value, fetcher=None, compatibility=None, transform_label=True, parent=None):
        ArgDataBase.__init__(self, arg, value, fetcher, compatibility, transform_label, parent)
        self.info_area = InfoArea(parent)

    def resolve(self):
        if self.label in ArgDataIP.DNS_CACHE:
            return

        self.fetcher.client.async().call('ufwi_log', 'resolveReverseDNS', self.label, callback=lambda x: self.resolved(self.label, x),
                                                                                    errback=lambda x: self.resolveFailed(self.label))

    def resolved(self, ip, dns):
        ArgDataIP.DNS_CACHE[self.label] = dns
        self.label = dns
        self.emit(SIGNAL('label_changed'))

    def resolveFailed(self, ip):
        try:
            message = unicode(self.tr("Unable to resolve %s")) % self.label
            self.info_area.setText(message)
        except RuntimeError:
            return # probably closing

    def printip(self):
        if self.label in ArgDataIP.DNS_CACHE.values():
            for key in ArgDataIP.DNS_CACHE:
                if ArgDataIP.DNS_CACHE[key] == self.label:
                    del ArgDataIP.DNS_CACHE[key]
                    break
            self.emit(SIGNAL('label_changed'))

    def actions(self):
        # Is label an already computed reverse DNS name ?
        if self.label in ArgDataIP.DNS_CACHE.values() and self.label not in ArgDataIP.DNS_CACHE:
                resolveAction = QAction(tr('Switch to IP address mode'), None)
                resolveAction.connect(resolveAction, SIGNAL('triggered()'), self.printip)
        else:
                resolveAction = QAction(tr('Resolve reverse DNS'), None)
                resolveAction.connect(resolveAction, SIGNAL('triggered()'), self.resolve)
        return [resolveAction]

    def ip2str(self, ip): return ip

    def _get_label(self):
        ipaddr = self.ip2str(self.label)
        try:
            dns = ArgDataIP.DNS_CACHE[ipaddr]
            if dns:
                return dns
            else:
                return ipaddr
        except KeyError:
            try:
                ip = IP(ipaddr)
            except ValueError:
                pass
            else:
                # FIXME this timer usage is responsible for the interface to get stuck
                # on packet list page during 10 sec
                #   Regit: I desactivate RDNS by default
                # Do not try to resolve *.0 and *.255 IP addresses.
                if False and ip.version() == 4 and not (ip.int() & 0xff) in (0, 255):
                #if ip.version() == 4 and not (ip.int() & 0xff) in (0,255):
                    # TODO add an option to activate the auto resolution
                    QTimer.singleShot(random.randint(0, 4000), self.resolve)
            return ipaddr

class ArgDataIPv6(ArgDataIP):
    def ip2str(self, ip):
        ipret = IP(ip, 6)
        if ipret.iptype() == 'IPV4COMP':
            return '::ffff:' + self.label.lstrip(':')
        else:
            return ipret.strCompressed()

class ArgDataIPv4(ArgDataIP):
    def ip2str(self, ip):
        return IP(int(ip), 4).strCompressed()

class ArgDataApp(ArgDataBase):
    def _get_label(self):
        """ Show only the filename """

        r = self.label.split('/')[-1].split('\\')[-1]
        if not r:
            return self.label
        else:
            return r

class ArgDataPort(ArgDataBase):

    # The signature isn't the same because this can be called with a proto parameter.
    # Note: this isn't used, so we could remove it. Problem is that in other case, we
    #       don't know what is the specified protocol for this port, and it might
    #       return an incorrect value.
    __pychecker__ = 'no-override'

    def _get_label(self, proto=None):
        """
            Show service associed of this port number.
            @arg proto [string] Only used if you want to call this function yourself
        """

        try:
            if proto:
                return socket.getservbyport(int(self.label), proto)
            #elif self.args.has_key('proto'):
            #    return socket.getservbyport(int(self.label), self.args['proto'])
            else:
                return socket.getservbyport(int(self.label))
        except (TypeError, ValueError):
            return self.label
        except socket.error:
            return self.label

class ArgDataBytes(ArgDataBase):
    units = [tr('B'),
             tr('KB'),
             tr('MB'),
             tr('GB'),
             tr('TB')]

    def _get_label(self):
        if not self.label:
            return ""
        num = float(self.label)
        for i in xrange(len(self.units)):
            n = num / 1024.0
            if n < 1:
                break
            num = n

        return '%.1f %s' % (num, self.units[i])

class ArgDataState(ArgDataBase):
    states = {-1:   tr('all'),
              0:    tr('dropped'),
              1:    tr('accepted'),
             }

    def _get_label(self):
        try:
            return self.states[int(self.label)]
        except (TypeError, ValueError, KeyError):
            return tr('unknown')

class ArgDataTimestamp(ArgDataBase):
    def _get_label(self):
        """ If this timestamp is a number, we create a date. """

        fmt = DATETIME_FORMAT
        try:
            timestamp = int(self.label)
            time = localtime(timestamp)
            now = localtime()
            if (time.tm_mday, time.tm_mon, time.tm_year) == \
               (now.tm_mday, now.tm_mon, now.tm_year):
                fmt = TIME_FORMAT
            return strftime(fmt, localtime(timestamp))
        except (TypeError, ValueError):
            if hasattr(self.label, 'strftime'):
                if hasattr(self.label, 'date') and datetime.today().date() == self.label.date():
                    fmt = TIME_FORMAT
                return self.label.strftime(fmt)
            return unicode(self.label)

class ArgDataUserGroups(ArgDataBase):
    def _fill_value(self, value):
        self.value = value
        without_domain = [name.split('@', 1)[0] for name in value]
        self.label = formatList(without_domain, ', ', 50)

    def _get_label(self):
        label = QLabel(self.label)
        tooltip = formatList(self.value, '\n', 500)
        label.setToolTip(tooltip)
        return label

