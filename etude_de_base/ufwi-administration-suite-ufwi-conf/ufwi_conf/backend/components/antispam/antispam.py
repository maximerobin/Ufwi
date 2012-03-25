#coding: utf-8
"""
Copyright (C) 2009-2011 EdenWall Technologies
Written by Pierre-Louis Bonicoli <bonicoli AT inl.fr>
"""

from __future__ import with_statement

from twisted.internet.defer import inlineCallbacks

from ufwi_rpcd.backend.exceptions import ConfigError
from ufwi_rpcd.core.context import Context
from ufwi_conf.backend.unix_service import ConfigServiceComponent
from ufwi_conf.common.antispam_cfg import AntispamConf

from error import ANTISPAM_BAD_CONFIGURATION
from error import NuConfError

class AntispamComponent(ConfigServiceComponent):
    """
    Manage the basic configuration of antispam
    """
    NAME = 'antispam'
    VERSION = '1.0'

    REQUIRES = ('config', 'hosts',)

    PIDFILE = '/var/run/spamd.pid'
    EXE_NAME = 'spamd'
    INIT_SCRIPT = 'spamassassin'

    # useless
    CONFIG = {}
    CONFIG_DEPENDS = ()

    ACLS = {
        'hosts': set(('getFqdn',)),
        'antispam': set(('status','start', 'stop')),
    }

    ROLES = {
        'conf_read': set(('getAntispamConfig',)),
        'conf_write': set(('setAntispamConfig',)),
    }

    def __init__(self):
        ConfigServiceComponent.__init__(self)
        self.addConfFile('/etc/spamassassin/local.cf', 'root:root', '0644')
        self.addConfFile('/etc/default/spamassassin', 'root:root', '0644')

        self.config = None

    def init(self, core):
        ConfigServiceComponent.init(self, core)

    def read_config(self, *args, **kwargs):
        try:
            self.config = self._read_config()
        except ConfigError:
            self.debug('config not loaded, load default')
            self.config = AntispamConf.defaultConf()

    def _read_config(self):
        serialized = self.core.config_manager.get(self.NAME)
        return AntispamConf.deserialize(serialized)

    def save_config(self, message, context=None):
        serialized = self.config.serialize()
        with self.core.config_manager.begin(self, context) as cm:
            try:
                cm.delete(self.NAME)
            except:
                pass
            cm.set(self.NAME, serialized)
            cm.commit(message)

    def should_run(self, responsible):
        return self.config.use_antispam

    @inlineCallbacks
    def genConfigFiles(self, responsible):
        templates_variables = {}
        for attr in AntispamConf.ATTRS:
            templates_variables[attr] = getattr(self.config, attr)
        context = Context.fromComponent(self)
        fqdn = yield self.core.callService(context, 'hosts', 'getFqdn')
        templates_variables['fqdn'] = fqdn
        templates_variables['use_antispam'] = self.config.use_antispam
        self.generate_configfile(templates_variables)

    # services
    def service_getAntispamConfig(self, context):
        return self.config.serialize()

    def service_setAntispamConfig(self, context, serialized, message):
        new_cfg = AntispamConf.deserialize(serialized)
        if new_cfg.isValid():
            self.config = new_cfg
            self.save_config(message, context)
        else:
            raise NuConfError(ANTISPAM_BAD_CONFIGURATION, 'invalid new configuration')
    # ... services

