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


from ufwi_rpcd.common import tr

#org
AD = "AD"
NND = "NND"
LDAP = "LDAP"
#auth
RADIUS = "RADIUS"
SAME = "SAME"
KERBEROS = "KERBEROS"
KERBEROS_AD = "KERBEROS_AD"
NOT_CONFIGURED = "NOT CONFIGURED"

def validcombinationsWithMsg(auth, org):
    if (auth == KERBEROS_AD) and (org != AD):
        return False, tr(
            "You can only authenticate users against "
            "Kerberos through Active Directory when Active Directory "
            "is selected for organizational reference."
            )
    return True, "Valid combination of protocols"

def getNetBiosName(hostname):
    if not hostname:
        return ''

    return hostname[:12]

#Ldap: require certificate?
REQCERT_VALUES = \
REQCERT_ALLOW, REQCERT_HARD = \
'allow','hard'

SSL_DISABLED = 'SSL_DISABLED'

