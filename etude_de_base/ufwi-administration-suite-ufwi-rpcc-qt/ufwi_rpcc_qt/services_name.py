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


from ufwi_rpcd.common import tr

class ComponentToName:
    COMPONENT_TO_NAME = None

    def __init__(self):
        if self.COMPONENT_TO_NAME is None:
            self.COMPONENT_TO_NAME = {
                'antispam': tr('Antispam'),
                'antivirus': tr('Antivirus'),
                'auth_cert': tr('Authentication Server'),
                'bind': tr('Name Server'),
                'dhcp': tr('DHCP Server'),
                'exim': tr('Mail Relay'),
                'ha': tr('High Availability'),
                'hostname': tr('Hostname'),
                'hosts': tr('Known hosts'),
                'network': tr('Network'),
                'network_ha': tr('Network configuration: services IPs'),
                'ntp': tr('Time Server'),
                'nuauth': tr('User Directory'),
                'nuauth_bind': tr('Name Server'),
                'nudpi': tr('Protocol Analysis'),
                'ufwi_rpcd_access': tr('NFAS Administration'),
                'nurestore': tr('Restoration Manager'),
                'openswan': tr('VPN (Site-to-Site)'),
                'openvpn': tr('Mobile VPN'),
                'resolv': tr('Domain name resolution'),
                'site2site': tr('VPN (site to site)'),
                'snmpd': tr('SNMP Server'),
                'squid': tr('Proxy Server'),
                'syslog_export': tr('Syslog export'),
                'ping_access': tr('Ping'),
                'access': tr('Access to services'),
            }

    def display_name(self, component):
        """
        return a displayable name for component
        """
        if component in self.COMPONENT_TO_NAME:
            return self.COMPONENT_TO_NAME[component]
        else:
            return component
