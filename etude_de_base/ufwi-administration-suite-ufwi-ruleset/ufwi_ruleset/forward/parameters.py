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
from os import umask, chmod
from os.path import join as path_join, exists
import re

from ufwi_rpcd.common.error import exceptionAsUnicode
from ufwi_rpcd.backend import tr
from ufwi_rpcd.backend.exceptions import ConfigError
from ufwi_rpcd.backend.variables_store import VariablesStore

from ufwi_ruleset.config import RULESET_DIR
from ufwi_ruleset.common.parameters import (
    LOCAL_FIREWALL, GATEWAY, NUFW_GATEWAY,
    LOG_LIMIT_REGEX_STR)
from ufwi_ruleset.forward.error import RulesetError

CONFIG_FILENAME = path_join(RULESET_DIR, "config.xml")

LOG_LIMIT_REGEX = re.compile(LOG_LIMIT_REGEX_STR)

class RulesetConfig:
    DEFAULT_VALUES = {
        'global': {
            'use_ipv6': True,
            'firewall_type' : GATEWAY,
        },
        'iptables': {
            'log_type': 'NFLOG',
            'log_limit': '',   # unlimited
            'default_drop': 'DROP',
            'nflog_group_accept': 2,
            'nflog_group_drop': 1,
            'nflog_group_reject': 1,
            'drop_invalid': True,
            'log_invalid': True,
        },
        'nufw': {
            'periods_filename': path_join(RULESET_DIR, 'periods.xml'),
            'require_group_name': False,
        },
        'ldap': {
            'host': "localhost",
            'port': 389,
            'username': "username",
            'password': "",
            'basedn': "basedn"
        }
    }

    def __init__(self, logger):
        self.store = VariablesStore()

        # Read the user configuration
        if exists(CONFIG_FILENAME):
            logger.info("Read the config")
            try:
                self.store.load(CONFIG_FILENAME)
            except ConfigError, err:
                logger.warning("Unable to read the config: %s" % exceptionAsUnicode(err))

        # Set missing values to the default value
        for section, values_dict in self.DEFAULT_VALUES.iteritems():
            for key, value in values_dict.iteritems():
                try:
                    self.store.get(section, key)
                except ConfigError:
                    self.store.set(section, key, value)

    def checkValue(self, section, key, value):
        if section == "global":
            if key == 'firewall_type':
                return value in (LOCAL_FIREWALL, GATEWAY, NUFW_GATEWAY)

        elif section == "iptables":
            if key == "log_type":
                return value in (u"LOG", u"ULOG", u"NFLOG")
            elif key == "default_drop":
                return value in (u"DROP", u"REJECT")
            elif key == "log_limit":
                return (not value) or bool(LOG_LIMIT_REGEX.match(value))
            elif key.startswith("nflog_group_"):
                # Group 0 is reserved bythe kernel (invalid packets)
                return (1 <= value  <= 65535)
        return True

    def checkNewConfig(self, config):
        for section in config.keys():
            for key, value in config[section].items():
                if key not in self[section]:
                    # ignore unknown key
                    continue
                if self[section][key] == value:
                    # No change
                    continue
                option_name = u"%s.%s" % (section, key)
                if not self.checkValue(section, key, value):
                    raise RulesetError(
                        tr('Invalid configuration value for the %s option: "%s"!'),
                        option_name, unicode(value))

    def setConfig(self, logger, new_conf):
        self.checkNewConfig(new_conf)

        logger.info("Write the config")
        for section in self.store:
            try:
                values = new_conf[section]
            except KeyError:
                continue
            for key, value in values.iteritems():
                self.store[section][key] = value

        umask(0077)
        self.store.save(CONFIG_FILENAME)
        # Force file permission if the file created outside ufwi_ruleset with the
        # wrong permissions
        chmod(CONFIG_FILENAME, 0600)

    def isGateway(self):
        return (self['global']['firewall_type'] != LOCAL_FIREWALL)

    def __getitem__(self, key):
        return self.store[key]

    def exportXMLRPC(self):
        return self.store.toDict()

