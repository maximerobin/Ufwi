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

from PyQt4.QtGui import QIntValidator, QRegExpValidator
from PyQt4.QtCore import QRegExp

from ufwi_rpcc_qt.central_dialog import (IPV4_REGEXP, IPV6_REGEXP,
        IP_ALL_REGEXP, IP_OR_FQDN_REGEXP, IP_OR_HOSTNAME_OR_FQDN_REGEXP,
        HOSTNAME_REGEXP, FQDN_REGEXP, MAIL_REGEXP, NET_ALL_REGEXP)

def hostOrIpValidator(parent):
    validator = QRegExpValidator(IP_OR_FQDN_REGEXP, parent)
    validator.setObjectName('hostOrIPValidator')
    return validator

def hostOrFqdnOrIpValidator(parent):
    validator = QRegExpValidator(IP_OR_HOSTNAME_OR_FQDN_REGEXP, parent)
    validator.setObjectName('hostOrFqdnOrIPValidator')
    return validator

def hostIPValidator(parent):
    validator = QRegExpValidator(IP_ALL_REGEXP, parent)
    validator.setObjectName('hostIPValidator')
    return validator

def hostIP6Validator(parent):
    validator = QRegExpValidator(IPV6_REGEXP, parent)
    validator.setObjectName('hostIP6Validator')
    return validator

def hostIP4Validator(parent):
    validator = QRegExpValidator(IPV4_REGEXP, parent)
    validator.setObjectName('hostIP4Validator')
    return validator

def hostnameValidator(parent):
    validator = QRegExpValidator(HOSTNAME_REGEXP, parent)
    validator.setObjectName('hostnameValidator')
    return validator

def netNameValidator(parent):
    validator = QRegExpValidator(FQDN_REGEXP, parent)
    validator.setObjectName('netNameValidator')
    return validator

def netValidator(parent):
    validator = QRegExpValidator(QRegExp(NET_ALL_REGEXP), parent)
    validator.setObjectName('netValidator')
    return validator

def portValidator(parent):
    validator = QIntValidator(0, 65535, parent)
    validator.setObjectName('portValidator')
    return validator

def proxyValidator(parent):
    # FIXME this regexp is buggy, it match 'https://:foo.be/'
    # it also match http://///
    validator = QRegExpValidator(QRegExp('^https?://(\S+(:\S+)?@)?(\S)+(:\d{1,5})?/?$'), parent)
    validator.setObjectName('proxyValidator')
    return validator

def mailValidator(parent):
    validator = QRegExpValidator(MAIL_REGEXP, parent)
    validator.setObjectName('mailValidator')
    return validator

