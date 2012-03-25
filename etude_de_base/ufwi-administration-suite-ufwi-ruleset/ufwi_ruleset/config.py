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

from os.path import join as path_join

# Directories
RULESET_DIR = '/var/lib/ufwi-ruleset'
LOCAL_RULES_IPV4_DIR = path_join(RULESET_DIR, 'local_rules_ipv4.d')
LOCAL_RULES_IPV6_DIR = path_join(RULESET_DIR, 'local_rules_ipv6.d')

# Create iptables filtering rules for IPv6
USE_IPV6 = True

PRODUCTION_RULESET = path_join(RULESET_DIR, "production_ruleset.xml")

