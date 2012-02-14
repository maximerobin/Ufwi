#coding: utf-8

"""
We group in this file the main logic for upgrading a User directory
configuration


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


from copy import deepcopy

from .protocols import AD
from .protocols import KERBEROS
from .protocols import KERBEROS_AD
from .protocols import LDAP
from .protocols import RADIUS
from .protocols import SAME

_3_AD_CLASS_NAME = 'ufwi_conf.common.user_dir.base.ADOrg'
_3_KERBEROS_AD_CLASS_NAME = 'ufwi_conf.common.user_dir.base.KerberosADAuth'
_3_KERBEROS_CLASS_NAME = 'ufwi_conf.common.user_dir.base.KerberosAuth'
_3_LDAP_CLASS_NAME = 'ufwi_conf.common.user_dir.base.LDAPOrg'
_3_RADIUS_CLASS_NAME = 'ufwi_conf.common.user_dir.base.RadiusAuth'
_3_SAME_CLASS_NAME = 'ufwi_conf.common.user_dir.base.SameAsOrgAuth'
_OLD_AD_CLASS_NAME = 'ufwi_conf.common.nuauthcfg.ADConf'
_OLD_LDAP_CLASS_NAME = 'ufwi_conf.common.nuauthcfg.LDAPConf'
_OLD_RADIUS_CLASS_NAME_A = 'ufwi_conf.common.nuauthcfg.RadiusConf'
_OLD_RADIUS_CLASS_NAME_B = 'ufwi_rpcd.common.radius_client.RadiusConf'

def _2to3_authclassesandversions(old_auth):
    if old_auth in (_OLD_LDAP_CLASS_NAME, _OLD_AD_CLASS_NAME):
        return _3_SAME_CLASS_NAME, 1
    elif old_auth in (_OLD_RADIUS_CLASS_NAME_A, _OLD_RADIUS_CLASS_NAME_B):
        return _3_RADIUS_CLASS_NAME, 1
    else:
        raise NotImplementedError(
            "This 'auth' value is unexpected in a < 3 serialized NuauthCfg: %s" % old_auth
            )

def _2to3_orgclassesandversions(old_org):
    if old_org == _OLD_LDAP_CLASS_NAME:
        return _3_LDAP_CLASS_NAME, 1
    elif old_org == _OLD_AD_CLASS_NAME:
        return _3_AD_CLASS_NAME, 1
    else:
        raise NotImplementedError(
            "This 'group' value is unexpected in a < 3 serialized NuauthCfg"
            )

def _upgradetype(serialized, typefinder):
    oldtype = serialized.get('__type__')
    newtype, newversion = typefinder(oldtype)
    serialized['__type__'] = newtype
    serialized['DATASTRUCTURE_VERSION'] = newversion

def _serializedprotocol(serialized):
    """
    On serialized NuauthCfg returns a tuple (authprotocol, orgprotocol)
    On auth or org returns protocol
    """
    _type = serialized.get('__type__')
    if _type.endswith('NuauthCfg'):
        #pre v3
        if 'group' in serialized:
            orgname = 'group'
        else:
            orgname = 'org'
        return (
            _serializedprotocol(serialized['auth']),
            _serializedprotocol(serialized[orgname])
            )
    if _type == _3_LDAP_CLASS_NAME:
        return LDAP
    elif _type == _3_AD_CLASS_NAME:
        return AD
    elif _type == _3_SAME_CLASS_NAME:
        return SAME
    elif _type == _3_RADIUS_CLASS_NAME:
        return RADIUS
    elif _type == _3_KERBEROS_CLASS_NAME:
        return KERBEROS
    #added in v3
    elif _type == _3_KERBEROS_AD_CLASS_NAME:
        return KERBEROS_AD

    raise NotImplementedError(
        "This 'nuautcfg' contains unexpected %s" % _type
        )

def upgradeNuauthCfg(serialized):
    """
    Makes an upgraded copy
    """
    upgraded = deepcopy(serialized)
    #Class names have changed
    #Also renaming 'group' to 'org'
    auth = upgraded.get('auth')
    org = upgraded.pop('group')
    upgraded['org'] = org
    _upgradetype(auth, _2to3_authclassesandversions)
    _upgradetype(org, _2to3_orgclassesandversions)

    #structure change
    protocols = _serializedprotocol(upgraded)
    if protocols == (SAME, LDAP):
        #LdapConf had a 'dn' value,
        #now we have 'dn_users' and 'dn_groups'
        org['dn_users'] = auth.pop('dn')
        org['dn_groups'] = org.pop('dn')
    elif protocols == (SAME, AD):
        #no change, yippee
        pass
    else:
        raise NotImplementedError("Sorry, this case is not handled")

    #Removing useless values
    del upgraded['group_reuse_auth']
    if protocols[0] == SAME:
        upgraded['auth'] = {
            'DATASTRUCTURE_VERSION': 1,
            '__type__': _3_SAME_CLASS_NAME
            }

    #DATASTRUCTURE_VERSION upgrade
    upgraded['DATASTRUCTURE_VERSION'] = 3
    return upgraded

