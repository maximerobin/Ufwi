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


from nucentral.backend.deps import Depends

ACCESS = 'access'
ANTISPAM = 'antispam'
ANTIVIRUS = 'antivirus'
AUTH_CERT = 'auth_cert'
BIND = 'bind'
CONTACT = 'contact'
DHCP = 'dhcp'
EXIM = 'exim'
HA = 'ha'
HOSTNAME = 'hostname'
HOSTS = 'hosts'
HTTPOUT = 'httpout'
IDS_IPS = 'ids_ips'
LICENSE = 'license'
NETWORK = 'network'
NETWORK_HA =  'network_ha'
NUAUTH = 'nuauth'
NUAUTH_BIND = 'nuauth_bind'
NTP = 'ntp'
OPENVPN = 'openvpn'
QUAGGA = 'quagga'
RESOLV = 'resolv'
SITE2SITE = 'site2site'
SNMPD = 'snmpd'
SQUID = 'squid'
STATUS = 'status'
SYSTEM = 'system'
TOOLS = 'tools'
UPDATE = 'update'

MODULES = tuple([ACCESS, ANTISPAM, ANTIVIRUS, AUTH_CERT, BIND, CONTACT, DHCP,
    EXIM, HA, HOSTNAME, HOSTS, HTTPOUT, IDS_IPS, LICENSE, NETWORK,
    NETWORK_HA, NUAUTH, NUAUTH_BIND, NTP, OPENVPN, QUAGGA, RESOLV,
    SITE2SITE, SNMPD, SQUID, STATUS, SYSTEM, TOOLS, UPDATE])

class TestDepends:
    def setup_class(cls):
        cls.deps = Depends()
        cls.deps.addDepObject(ACCESS, set([NETWORK]))
        cls.deps.addDepObject(ANTISPAM, set())
        cls.deps.addDepObject(ANTIVIRUS, set())
        cls.deps.addDepObject(AUTH_CERT, set())
        cls.deps.addDepObject(BIND, set((NETWORK, RESOLV)))
        cls.deps.addDepObject(CONTACT, set())
        cls.deps.addDepObject(DHCP, set([NETWORK]))
        cls.deps.addDepObject(EXIM, set([ANTIVIRUS]))
        cls.deps.addDepObject(HA, set((HOSTNAME, NETWORK_HA, NETWORK)))
        cls.deps.addDepObject(HOSTNAME, set())
        cls.deps.addDepObject(HOSTS, set((RESOLV, HOSTNAME)))
        cls.deps.addDepObject(HTTPOUT, set())
        cls.deps.addDepObject(IDS_IPS, set())
        cls.deps.addDepObject(LICENSE, set())
        cls.deps.addDepObject(NETWORK, set())
        cls.deps.addDepObject(NETWORK_HA, set((HOSTNAME, NETWORK)))
        cls.deps.addDepObject(NTP, set())
        cls.deps.addDepObject(NUAUTH, set([NUAUTH_BIND]))
        cls.deps.addDepObject(NUAUTH_BIND, set())
        cls.deps.addDepObject(OPENVPN, set((NETWORK, RESOLV)))
        cls.deps.addDepObject(QUAGGA, set())
        cls.deps.addDepObject(RESOLV, set())
        cls.deps.addDepObject(SITE2SITE, set())
        cls.deps.addDepObject(SNMPD, set())
        cls.deps.addDepObject(SQUID, set())
        cls.deps.addDepObject(STATUS, set())
        cls.deps.addDepObject(SYSTEM, set())
        cls.deps.addDepObject(TOOLS, set())
        cls.deps.addDepObject(UPDATE, set([HTTPOUT]))

    def test_orderedDependences(self):
        """
        test method Depends.getOrderedDependences(...)
        """
        #And now the big tests !
        for data, expected in (
            # expected are objects wich are awaken when data is modified
            ((NETWORK), set((NETWORK, HA, BIND, DHCP, ACCESS, OPENVPN, NETWORK_HA))),
            ((HOSTNAME), set((HOSTNAME, HA, HOSTS, NETWORK_HA))),
            ((HA), set((HA,))),
            ((NETWORK_HA), set((NETWORK_HA, HA,))),
            ):
            received = self.deps.getOrderedDependences(data)

            assert expected == set(received), "for %s :\n\nexpected %s / received %s\n\tdiff %s" % ( data, expected, set(received), expected.symmetric_difference(received))


    def test_getDependancesForMany_1(self):
        """
        simple test method Depends.getDependancesForMany(...)
        test multiple modifiations
        """
        data = [NETWORK_HA, HOSTNAME]
        expected = ([HOSTNAME, HOSTS, NETWORK_HA, HA],
                    [HOSTNAME, NETWORK_HA, HOSTS, HA],
                    [HOSTNAME, NETWORK_HA, HA, HOSTS])

        received = self.deps.getDependancesForMany(data)
        assert received in expected, "for %s :\n\nexpected %s / received %s" % ( data, expected, received)

    def test_getDependancesForMany_2(self):
        """
        complete test method Depends.getDependancesForMany(...)
        test multiple modifiations
        """
        received = self.deps.getDependancesForMany(MODULES)
        print MODULES, received
        for module, mod_depend in ((ACCESS, NETWORK), (BIND, NETWORK), (BIND, RESOLV),
            (DHCP, NETWORK), (EXIM, ANTIVIRUS), (HA, HOSTNAME), (HA, NETWORK),
            (HA, NETWORK_HA), (HOSTS, RESOLV), (HOSTS, HOSTNAME),
            (NUAUTH, NUAUTH_BIND), (OPENVPN, RESOLV), (OPENVPN, RESOLV),
            (UPDATE, HTTPOUT)):
            print "%s loaded after %s" % (module, mod_depend)
            assert received.index(module) > received.index(mod_depend),\
                "module %(mod)s depend of %(dep)s, %(mod)s must be loaded after %(dep)s"\
                % ({'mod':module, 'dep':mod_depend})

        rmodules = list(MODULES)
        rmodules.reverse()
        received = self.deps.getDependancesForMany(rmodules)
        print rmodules, received
        for module, mod_depend in ((ACCESS, NETWORK), (BIND, NETWORK), (BIND, RESOLV),
            (DHCP, NETWORK), (EXIM, ANTIVIRUS), (HA, HOSTNAME), (HA, NETWORK),
            (HA, NETWORK_HA), (HOSTS, RESOLV), (HOSTS, HOSTNAME),
            (NUAUTH, NUAUTH_BIND), (OPENVPN, RESOLV), (OPENVPN, RESOLV),
            (UPDATE, HTTPOUT)):
            print "%s loaded after %s" % (module, mod_depend)
            assert received.index(module) > received.index(mod_depend),\
                "module %(mod)s depend of %(dep)s, %(mod)s must be loaded after %(dep)s"\
                % ({'mod':module, 'dep':mod_depend})
