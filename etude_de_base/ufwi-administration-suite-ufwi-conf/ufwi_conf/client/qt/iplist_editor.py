# -*- coding: utf-8 -*-
"""
$Id$


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


from IPy import IP
from PyQt4.QtGui import QTextEdit
from ufwi_rpcd.common import tr
from ufwi_conf.client.system.ha import QHAObject
try:
    from ufwi_conf.common.ha_statuses import ENOHA
    USE_HA_MODULE = True
except ImportError:
    USE_HA_MODULE = False
from .validable import Validable
from .exceptions import InputException

class AbstractIPListEdit(Validable, QTextEdit):
    def __init__(self, parent=None, accept_empty=False):
        QTextEdit.__init__(self, parent)
        Validable.__init__(self, accept_empty=accept_empty)
        self.setTabChangesFocus(True)
        self.setAcceptRichText(True)
        self.setWhatsThis(tr('<h3><font color="blue">IP List</font></h3>'
            'Enter a list of IP addresses separated by spaces or carriage returns.<br/>'))

    def _text(self):
        return unicode(self.toPlainText()).strip()

    def getFieldInfo(self):
        return tr("IP addresses")

    def focusInEvent(self, event):
        Validable.focusInEvent(self, event)
        QTextEdit.focusInEvent(self, event)

    def focusOutEvent(self, event):
        Validable.focusOutEvent(self, event)
        QTextEdit.focusOutEvent(self, event)

class IpListEdit(AbstractIPListEdit):

    def setIpAddrs(self, ip_addrs):
        self.clear()
        for ip in ip_addrs:
            self.append("%s\n" % unicode(ip))

    def isValid(self, accept_empty=True):
        text = self._text()
        if text == '':
            return accept_empty or self.accept_empty
        return all (self._isValid(value.strip()) for value in text.split())

    @classmethod
    def _isValid(cls, value):
        try:
            value = IP(value)
        except:
            return False
        return "/" not in unicode(value)

    def __iter__(self):
        for value in self._text().split():
            yield IP(value)

    def isEmpty(self):
        try:
            for value in self:
                return True
        except Exception:
            pass
        return False

    def value(self):
        result = set()
        for ip in self:
            result.add(ip)
        return result

class NetIpListEdit(AbstractIPListEdit):
    def __init__(self, net, parent=None, accept_empty=False):
        AbstractIPListEdit.__init__(self, parent, accept_empty)

        if USE_HA_MODULE:
            ha_cfg = QHAObject.getInstance().hacfg
            if ha_cfg is None or ha_cfg.ha_type == ENOHA:
                self.service = ""
            else:
                self.service = " service"
        else:
            self.service = ""

        self.fill(net)
        self._nok_stylesheet = ''

    def fill(self, net):
        for ip in net.service_ip_addrs:
            self.append("%s%s" % (unicode(ip), self.service))
        for ip in net.primary_ip_addrs:
            self.append("%s primary" % unicode(ip))
        for ip in net.secondary_ip_addrs:
            self.append("%s secondary" % unicode(ip))

    def values(self):
        service = set()
        primary = set()
        secondary = set()

        text = self._text()
        text = text.replace('\n', '<br/>')

        for line_number, value in enumerate(
            self._text().splitlines()
            ):

            split_value = value.split()

            words = len(split_value)
            if words == 0:
                continue
            if words > 2:
                text = text.replace(value, '<span style="color:red">' + value + '</span>')
                self.setHtml(text)
                raise InputException(tr("Too many words on line %i") % (line_number + 1))

            ip = split_value[0]

            if words == 1:
                category = service
            elif words == 2:
                unparsed_category = split_value[1].lower()
                if unparsed_category == "primary":
                    category = primary
                    #212483: edenwall blue 33, 36, 131
                    text = text.replace(value, '<span style="color:#212483">' + value + '</span>')
                elif unparsed_category == "secondary":
                    category = secondary
                    #196d38: edenwall green 25, 109, 56
                    text = text.replace(value, '<span style="color:green">' + value + '</span>')
                elif unparsed_category == "service":
                    category = service
                    if words == 1:
                        text = text.replace(value, '<span>' + value + " " + self.service + '</span>')
                else:
                    text = text.replace(value, '<span style="color:red">' + value + '</span>')
                    self.setHtml(text)
                    raise InputException(
                        tr(
                            "Unsupported IP specification: '%s'\n"
                            "Supported IP specifications are 'primary', 'secondary', 'service' \n"
                            "or none (defaults to service)."
                        ) % unicode(unparsed_category)
                        )
            ipy = IP(ip)
            if ipy in service | secondary | primary:
                #d3696c: edenwall lighter red
                text = text.replace(
                        ip,
                        '<span style="background-color:#d3696c">%s</span>' % ip
                    )
                self.setHtml(text)
                raise InputException(
                tr(
                    "Warning, the same IP address is specified more than once: %s."
                ) % ip
                )

            category.add(ipy)

        self.setHtml(text)
        return {
            'primary': primary,
            'secondary': secondary,
            'service': service
            }

    def isValidWithMsg(self, accept_empty=True, message=False):
        text = self._text()
        if text == '':
            if accept_empty or self.accept_empty:
                return True, None
            else:
                return False, tr("Empty field.")

        try:
            values = self.values()
        except InputException, err:
            message = tr("Unsupported IP specification: ")
            message += "<br/>"
            message += tr(
                "Supported IP specifications are «primary», «secondary», «service»"
                "or none (defaults to service)."
                )
            if len(err.args) >= 2:
                message += "<br/>"
                message += tr("But found %s") % err.args[1]
            message = "<span>%s</span>" % message
            return False, message
        except Exception, err:
            return False, unicode(err.args)

        # Check all ip are different
        all_ips = values['primary'] | values['secondary'] | values['service']

        if len(all_ips) != len(values['primary']) + len(values['secondary']) + len(values['service']):
            invalid_ips = values['primary'] & values['secondary']
            invalid_ips |= values['primary'] & values['service']
            invalid_ips |= values['secondary'] & values['service']
            return False, tr("You cannot set the same IP multiple times. (%s)") % ','.join(str(ip) for ip in invalid_ips)

        no_primary = len(values['primary']) == 0
        no_secondary = len(values['secondary']) == 0

        if no_secondary == no_primary:
            return True, ""
        else:
            return False, tr("If there are 'primary' addresses, there must be 'secondary' addresses too.")

    def isValid(self, accept_empty=True):
        ok, msg = self.isValidWithMsg(accept_empty=accept_empty)
        return ok

class NetworkListEdit(IpListEdit):
    def __init__(self, parent=None):
        IpListEdit.__init__(self, parent)
        self.setWhatsThis(tr('<h3><font color="blue">%s</font></h3>%s<br/>') % (
            tr('Network List'),
            tr('Enter a list of Network addresses separated by spaces or carriage returns.'))
        )

    def __iter__(self):
        for value in self._text().split():
            yield IP(value, make_net=True)

    def getFieldInfo(self):
        return tr("Network addresses")

    @classmethod
    def _isValid(cls, value):
        try:
            value = IP(value, make_net=True)
        except Exception:
            return False
        return True


