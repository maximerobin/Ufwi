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

from __future__ import with_statement

from ufwi_ruleset.forward.flatten import flattenObjectList

def objectsMatch(objects_a, objects_b):
    """
    Return True if at least one object of objects_a matchs an object of
    objects_b, otherwise return False.
    """
    for obja in flattenObjectList(objects_a):
        for objb in flattenObjectList(objects_b):
            if obja.match(objb):
                return True
    return False

def objectsOverlap(objects_a, objects_b):
    """
    Return True if at least one object of objects_a overlaps an object of
    objects_b, otherwise return False.
    """
    for obja in flattenObjectList(objects_a):
        for objb in flattenObjectList(objects_b):
            if obja.overlaps(objb):
                return True
    return False

def matchAddresses(addresses_a, addresses_b):
    """
    Return True if at least one address of addresses_a is a superset on a
    address of addresses_b, otherwise return False.

    >>> from IPy import IP
    >>> matchAddresses([IP('192.168.0.0/24')], [IP('192.168.0.1')])
    True
    >>> matchAddresses([IP('192.168.0.0/24')], [IP('10.0.0.0/8')])
    False
    """
    for addra in addresses_a:
        for addrb in addresses_b:
            if addrb in addra:
                return True
    return False

def aclCollisionA(rule_a, rule_b, result):
    # rule_a is a superset of rule_b for the attributes sources, protocols and
    # destinations
    auth_a = bool(rule_a.user_groups)
    auth_b = bool(rule_b.user_groups)
    if auth_a and auth_b:
        match = rule_a.match(rule_b, ('user_groups',))
        if not match:
            # No conflict:
            #
            #  ACL #1: LAN --http--> Internet, user=admin, decision=ACCEPT
            #  ACL #1: LAN --http--> Internet, user=users, decision=DROP
            return False
    # Conflicts:
    #
    #  ACL #1: LAN --http--> Internet
    #  ACL #2: LAN --http--> Internet
    #
    # or
    #
    #  ACL #1: LAN --http--> Internet, user=admin
    #  ACL #2: LAN --http--> Internet
    #
    # or
    #
    #  ACL #1: LAN --http--> Internet
    #  ACL #2: LAN --http--> Internet, user=admin
    #
    # or
    #
    #  ACL #1: LAN --http--> Internet, user=admin, decision=ACCEPT
    #  ACL #2: LAN --http--> Internet, user=admin, decision=DROP
    blocker = not(auth_a ^ auth_b)
    result.hiddenRule(rule_b, rule_a, blocker)
    return True

def aclConsistencyTests(rule_a, rule_b, result):
    # rule_a is before rule_b in the ACL chain
    match = rule_a.match(rule_b, ('sources', 'destinations', 'protocols'))
    if match:
        if aclCollisionA(rule_a, rule_b, result):
            # Don't call _aclsOverlap() to avoid
            # displaying the same message twice!
            return

    if rule_a.user_groups \
    and (not rule_b.user_groups) \
    and rule_a.overlaps(rule_b, ('sources', 'destinations', 'protocols')):
        # Conflict (host is part of the LAN):
        #
        #  ACL #1: host --http--> Internet, user=admin
        #  ACL #2: LAN --http--> Internet
        #
        # "toto" user connect from "host" is blocked
        result.hiddenRule(rule_b, rule_a, True)

def aclsConsistencyTests(rules, result):
    for index, rule_a in enumerate(rules):
        for rule_b in rules[index+1:]:
            aclConsistencyTests(rule_a, rule_b, result)

