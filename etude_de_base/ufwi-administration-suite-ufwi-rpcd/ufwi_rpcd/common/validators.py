# -*- coding: utf-8 -*-

# $Id$

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


from IPy import IP
import re
from ufwi_rpcd.common.network import HOSTNAME_REGEX_STR, IPV4_REGEX_STR, \
    IPV6_REGEX_STR, HOSTNAME_OR_FQDN_REGEX_STR, MAIL_REGEX_STR, DN_REGEXP_STR

HOSTNAME_REGEX = re.compile(HOSTNAME_REGEX_STR, re.IGNORECASE)
def check_hostname(value):
    return HOSTNAME_REGEX.match(value) is not None

IP_REGEX = re.compile('^(?:%s|%s)$' % (IPV4_REGEX_STR, IPV6_REGEX_STR))
def check_ip(value):
    """
    Make sure that value is a valid IPv4 or IPv6 value.
    """
    if not IP_REGEX.match(value):
        return False
    try:
        IP(value)
    except ValueError:
        return False
    return True

def check_port(value):
    try:
        i = int(value)
        if 0 < i < 65536:
            return True
    except ValueError:
        pass
    return False

def check_network(value):
    try:
        return IP(value, make_net=True)
    except Exception:
        return False

DOMAIN_REGEX = re.compile(HOSTNAME_OR_FQDN_REGEX_STR, re.IGNORECASE)
def check_domain(value):
    return DOMAIN_REGEX.match(value) is not None

def check_ip_or_domain(value):
    return check_ip(value) or check_domain(value)

MAIL_REGEX = re.compile('^%s$' % MAIL_REGEX_STR, re.IGNORECASE)
def check_mail(value):
    return MAIL_REGEX.match(value) is not None

DN_REGEX = re.compile('^%s$' % DN_REGEXP_STR, re.IGNORECASE)
def check_dn(value):
    return DN_REGEX.match(value) is not None

