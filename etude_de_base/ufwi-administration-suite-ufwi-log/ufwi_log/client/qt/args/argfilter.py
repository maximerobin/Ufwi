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

from PyQt4.QtGui import QLineEdit, QSpinBox, QComboBox, QDateTimeEdit
from PyQt4.QtCore import QVariant, QDateTime, SIGNAL

from ufwi_rpcd.common.error import UnicodeException
from ufwi_rpcd.common import tr
import re
from IPy import IP

class CheckError(UnicodeException):
    """
        This exception is raised when a check() call in
        a ArgFilterBase derived object fails.
    """
    pass

class ArgFilterBase:
    """
        Base class of Arg objects.
        Note that it can be or not a filter.
    """

    OLD_VALUE = {}

    def __init__(self, client, arg, value, compatibility=None):
        """
            Constructor
            @param arg  [unicode] this is the name of argument
            @param value  [unicode] value of this argument
        """

        self.client = client
        self.filter_arg = arg
        self.filter_value = value
        self.list = []
        self.compatibility = compatibility

        if not self.filter_value and self.OLD_VALUE and unicode(type(self)) in self.OLD_VALUE:
            self.filter_value = self.OLD_VALUE[unicode(type(self))]

            if isinstance(self, QLineEdit):
                self.setText(self.filter_value)
            elif isinstance(self, QSpinBox):
                self.setValue(self.filter_value)

    def done(self, res):
        ArgFilterBase.OLD_VALUE.clear()

    def getValue(self):
        raise NotImplementedError()

class ArgFilterForbidden(ArgFilterBase):

    def getValue(self):
        """ This function is used if argument linked is forbidden """
        raise CheckError(tr('%s is not a valid argument name') % self.filter_arg)

class ArgFilterText(ArgFilterBase, QLineEdit):
    def __init__(self, client, arg, value, compatibility=None):
        QLineEdit.__init__(self, unicode(value))
        ArgFilterBase.__init__(self, client, arg, value, compatibility=compatibility)

    def getValue(self):
        return unicode(self.text())

    def textChanged(self, text):
        ArgFilterBase.OLD_VALUE[unicode(type(self))] = unicode(self.text())

class ArgFilterIP(ArgFilterText):

    #          is ip, regexp
    regexps = [(True, re.compile('^[0-9a-fA-F:]+:[0-9a-fA-F:]+(/[0-9]{1,3})*$')), # ipv6
               (True, re.compile('^[0-9]{1,3}(\\.[0-9]{1,3}){3}(/[0-9]{1,2})*$')), # ipv4
               (False, re.compile('^[a-z][a-z0-9_-]*(\\.[a-z][a-z0-9_-]*)*$'))] # hostname
    def __init__(self, client, arg, value, compatibility=None):
        ArgFilterText.__init__(self, client, arg, value, compatibility=compatibility)
        self.connect(self, SIGNAL("textChanged(const QString&)"), self.textChanged)
        self.setToolTip(self.tr('Enter an IP, a CIDR mask or a hostname.'))

    def textChanged(self, s):
        if self.isEnabled():
            ArgFilterText.textChanged(self, s)
            try:
                self.getValue()
                valid = True
            except CheckError:
                valid = False
        else:
            valid = True
        if valid:
            style = ''
        else:
            style = 'background: #b52323;'
        self.setStyleSheet(style)

    def getValue(self):
        """ This function is useless because now we can give an hostname """
        self.filter_value = ArgFilterText.getValue(self)
        for ip, regexp in self.regexps:
            if regexp.match(self.filter_value):
                if ip:
                    try:
                        IP(self.filter_value)
                    except:
                        break
                return self.filter_value

        raise CheckError(tr('Please enter a valid IP address, CIDR mask or hostname:\n%s') % self.filter_value)

class ArgFilterIntIP(ArgFilterIP):

    def __init__(self, client, arg, value, compatibility=None):
        if value == '':
            return ArgFilterIP.__init__(self, client, arg, value, compatibility=compatibility)
        if 'ipv4' in arg:
            value = unicode(IP(int(value), 4))
        else:
            value = unicode(IP(int(value), 6))

        ArgFilterIP.__init__(self, client, arg, value)

    def getValue(self):
        value = ArgFilterIP.getValue(self)
        return unicode(IP(value).int())

class ArgFilterInt(ArgFilterBase, QSpinBox):
    """ Argument is an integer """

    def __init__(self, client, arg, value, compatibility=None):

        QSpinBox.__init__(self)
        ArgFilterBase.__init__(self, client, arg, value, compatibility=compatibility)
        self.setMinimum(0)
        self.setMaximum(2147483647) # 2^31-1
        self.connect(self, SIGNAL('valueChanged( int )'), self.newValue)
        try:
            self.setValue(int(value))
        except (TypeError, ValueError):
            # this is not an integer
            pass

    def newValue(self, value):
        ArgFilterBase.OLD_VALUE[unicode(type(self))] = int(value)
        self.setValue(int(value))

    def getValue(self):
        self.OLD_VALUE[unicode(type(self))] = QSpinBox.value(self)
        return QSpinBox.value(self)

class ArgFilterPort(ArgFilterInt):
    """ Argument is a filter AND a port """

    def __init__(self, client, arg, value, compatibility=None):
        ArgFilterInt.__init__(self, client, arg, value, compatibility=compatibility)
        self.setMinimum(0)
        self.setMaximum(65535)

class ArgFilterProto(ArgFilterBase, QComboBox):
    """ Argument is a protocol name AND a filter """

    def __init__(self, client, arg, value, compatibility=None):

        ArgFilterBase.__init__(self, client, arg, value, compatibility=compatibility)
        QComboBox.__init__(self)

        self.addItem(tr('TCP'), QVariant('tcp'))
        self.addItem(tr('UDP'), QVariant('udp'))
        self.addItem(tr('ICMP'), QVariant('icmp'))
        self.addItem(tr('IGMP'), QVariant('igmp'))

        index = self.findData(QVariant(value))
        if index >= 0:
            self.setCurrentIndex(index)

    def getValue(self):

        return unicode(self.itemData(self.currentIndex()).toString())

class ArgFilterState(ArgFilterBase, QComboBox):

    def __init__(self, client, arg, value, compatibility=None):

        ArgFilterBase.__init__(self, client, arg, value, compatibility=compatibility)
        QComboBox.__init__(self)

        self.addItem(tr('All'), QVariant(-1))
        self.addItem(tr('Dropped'), QVariant(0))
        self.addItem(tr('Accepted'), QVariant(1))

        try:
            index = self.findData(QVariant(int(value)))
            if index >= 0:
                self.setCurrentIndex(index)
        except (TypeError, ValueError):
            return

    def getValue(self):
        return int(self.itemData(self.currentIndex()).toInt()[0])

class ArgFilterProxyState(ArgFilterBase, QComboBox):

    def __init__(self, client, arg, value, compatibility=None):

        ArgFilterBase.__init__(self, client, arg, value, compatibility=compatibility)
        QComboBox.__init__(self)

        self.addItem(tr('Dropped'), QVariant('dropped'))
        self.addItem(tr('Accepted'), QVariant('accepted'))

        try:
            index = self.findData(QVariant(value))
            if index >= 0:
                self.setCurrentIndex(index)
        except (TypeError, ValueError):
            return

    def getValue(self):
        return unicode(self.itemData(self.currentIndex()).toString())

class ArgFilterFirewall(ArgFilterBase, QComboBox):

    def __init__(self, client, arg, value, compatibility=None):

        ArgFilterBase.__init__(self, client, arg, value, compatibility=compatibility)
        QComboBox.__init__(self)

        if self.client.call('CORE', 'hasComponent', 'multisite_master'):
            firewalls = self.client.call('multisite_master', 'listFirewalls')
            firewalls.sort()
            for fw, state, error, last_seen, ip in firewalls:
                self.addItem(fw, QVariant(fw))
            index = self.findData(QVariant(value))
            if index >= 0:
                self.setCurrentIndex(index)
            else:
                self.insertItem(0, value, QVariant(value))
                self.setCurrentIndex(0)
        else:
            self.addItem(self.tr('This'), QVariant(''))

    def getValue(self):
        return unicode(self.itemData(self.currentIndex()).toString())

class ArgFilterUserID(ArgFilterBase, QComboBox):

    # States
    NOLIST = 0
    LIST = 1
    SELECTED = 2

    def __init__(self, client, arg, value, compatibility=None):

        ArgFilterBase.__init__(self, client, arg, value, compatibility)
        QComboBox.__init__(self)
        assert compatibility is not None

        self.setEditable(True)
        self.users = []
        self.setDuplicatesEnabled(False)

        # This attribut is used to prevent an infinite loop
        # when we change text or list values as we are in the
        # editTextChanged callback.
        self.lock = False

#        if value and (isinstance(value, (int,long)) or isinstance(value, (str, unicode)) and value.isdigit()):
        if value:
            if self.compatibility.user_id:
                userlist = self.client.call('ufwi_log', 'table', 'UserIDTable', {'user_id': value})
            else:
                userlist = self.client.call('ufwi_log', 'table', 'UserIDTable', {'username': value})

            if userlist:
                if self.compatibility.user_id:
                    self.textChanged(userlist[0][0])
                else:
                    self.textChanged(userlist[0])
            else:
                self.textChanged('') # to initialize state to NOLIST
        else:
            self.textChanged('') # to initialize state to NOLIST

        self.connect(self, SIGNAL('currentIndexChanged(int)'), self.indexChanged)
        self.connect(self, SIGNAL('editTextChanged(const QString &)'), self.textChanged)

    def setState(self, s):
        self.state = s
        style = ''
        if self.isEnabled() and len(self.lineEdit().text()) > 0:
            if self.state == self.NOLIST:
                style = 'background: #b52323;' # red
            elif self.state == self.LIST:
                style = 'background: #B5AD1C;' # orange
            elif self.state == self.SELECTED:
                style = 'background: #5FB554;' # green
        self.setStyleSheet(style)

    def indexChanged(self, index):
        if self.state == self.NOLIST:
            return

        self.setState(index >= 0 and self.SELECTED or self.LIST)

    def textChanged(self, text):

        # Is this callback called because of a text modification
        # in an other call of this method in call stack.
        # It prevents an infinite loop.
        if self.lock:
            return

        # Do not check list for one letter unexistant accounts
        if len(text) < 2:
            self.lock = True
            self.setState(self.NOLIST)
            self.clear()
            self.users = []
            self.addItem(tr('-- Please enter at least two letters --'), QVariant(-1))
            self.setCurrentIndex(-1)
            self.lineEdit().setText(text)
            self.lock = False
            return

        self.lock = True
        self.clear()
        if not self.users:
            self.users = self.client.call('ufwi_log', 'table', 'UserIDTable', {'username': '%s%%' % text[:2]})

            users2 = []

            if self.compatibility.authfail:
                users2 = self.client.call('ufwi_log', 'table', 'UserIDTableAuth', {'username': '%s%%' % text[:2]})
                if not self.compatibility.user_id:
                    self.users = list(set(self.users + users2))
                else:
                    for user2 in users2:
                        if len(user2) > 1:
                            contains = False
                            for user1 in self.users:
                                if len(user1) > 1:
                                    if user1 == user2:
                                        contains = True
                                        break
                            if not contains:
                                self.users.append(user1)

        select = -1
        added_users = []

        for username in self.users:
            if self.compatibility.user_id:
                user_id = username[1]
                username = username[0]
                variant = QVariant(user_id)
            else:
                variant = QVariant(username)

            if username.startswith(text) and not username in added_users:
                self.addItem(username, variant)
                added_users.append(username)
                if username == text:
                    select = self.count() - 1

        self.setCurrentIndex(select)
        if select >= 0:
            self.setState(self.SELECTED)
        else:
            # Reset text, because of the adding of lines in list
            self.lineEdit().setText(text)
            if len(self.users) > 0:
                self.setState(self.LIST)
            else:
                self.setState(self.NOLIST)

        self.lock = False

    def getValue(self):

        selected = -1
        if self.state == self.SELECTED:
            selected = unicode(self.itemData(self.currentIndex()).toString())
        if not selected:
            raise CheckError(tr('Please select a user from the list'))

        return selected

class ArgFilterTimestamp(ArgFilterBase, QDateTimeEdit):

    def __init__(self, client, arg, value, compatibility=None):
        ArgFilterBase.__init__(self, client, arg, value, compatibility=compatibility)
        QDateTimeEdit.__init__(self)

        datevalue = QDateTime()
        try:
            datevalue.setTime_t(int(value))
            self.setDateTime(datevalue)
        except (TypeError, ValueError):
            self.setDateTime(QDateTime.currentDateTime())

        self.setCalendarPopup(True)

    def getValue(self):
        """ Return the timestamp from the date string """

        return self.dateTime().toTime_t();

class ArgFilterDatetime(ArgFilterBase, QDateTimeEdit):

    def __init__(self, client, arg, value, compatibility=None):
        ArgFilterBase.__init__(self, client, arg, value, compatibility=compatibility)
        QDateTimeEdit.__init__(self)

        datevalue = QDateTime()
        try:
            datevalue.setTime_t(int(value))
            self.setDateTime(datevalue)
        except (TypeError, ValueError):
            self.setDateTime(QDateTime.currentDateTime())

        self.setCalendarPopup(True)

    def getValue(self):
        """ Return the datetime string from the date string """

        return unicode(self.dateTime().toString())

