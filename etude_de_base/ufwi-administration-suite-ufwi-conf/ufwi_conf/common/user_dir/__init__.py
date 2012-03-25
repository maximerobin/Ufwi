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
--
Auth/organization config for nuauth
"""

from .base import (NuauthCfg, ADOrg, KerberosAuth, KerberosADAuth, LDAPOrg,
    RadiusAuth, SameAsOrgAuth, NotConfiguredAuth, NndOrg, NotConfiguredOrg)

from .protocols import (AD, NND, KERBEROS, KERBEROS_AD, LDAP, RADIUS,
    SAME, NOT_CONFIGURED)

protocols = (AD, LDAP, RADIUS, SAME, NOT_CONFIGURED)
auth_protocols = (RADIUS, SAME, KERBEROS, KERBEROS_AD, NOT_CONFIGURED)
org_protocols = (AD, NND, LDAP, NOT_CONFIGURED)

def auth_class(protocol):
    """
    auth class to be used for config of a protocol
    """
    if protocol == RADIUS:
        return RadiusAuth
    elif protocol == KERBEROS:
        return KerberosAuth
    elif protocol == KERBEROS_AD:
        return KerberosADAuth
    elif protocol == SAME:
        return SameAsOrgAuth
    elif protocol == NOT_CONFIGURED:
        return NotConfiguredAuth
    raise NotImplementedError(protocol)

def org_class(protocol):
    """
    org to be used for config of a protocol
    """
    if protocol == AD:
        return ADOrg
    elif protocol == NND:
        return NndOrg
    elif protocol == LDAP:
        return LDAPOrg
    elif protocol == NOT_CONFIGURED:
        return NotConfiguredOrg
    raise NotImplementedError(protocol)

