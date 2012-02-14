# -*- coding: utf-8 -*-
"""
Copyright (C) 2009-2011 EdenWall Technologies
Written by Pierre-Louis Bonicoli <bonicoli AT inl.fr>
$Id$
"""
from __future__ import with_statement

from ufwi_rpcd.common.service_status_values import ServiceStatusValues
from ufwi_rpcd.core.context import Context
from ufwi_conf.backend.unix_service import ConfigServiceComponent

class AntivirusComponent(ConfigServiceComponent):
    """
    Manage the basic configuration of antivirus
    """
    NAME = 'antivirus'
    VERSION = '1.0'

    REQUIRES = ('config', )

    PIDFILE = '/var/run/clamav/clamd.pid'
    EXE_NAME = 'clamd'
    INIT_SCRIPT = 'clamav-daemon'

    # useless
    CONFIG = {}
    CONFIG_DEPENDS = ()

    ACLS = { 'antivirus': set(('status', 'start', 'stop', 'restart')), }

    ROLES = {
        'ufwi_conf_write': set(('use','start', 'stop')),
    }

    def __init__(self):
        ConfigServiceComponent.__init__(self)
        self.addConfFile('/etc/clamav/clamd.conf', 'root:root', '0644')
        # by default antivirus is disabled
        self.used_by = {} # component name : used/unused (bool)

    def init(self, core):
        ConfigServiceComponent.init(self, core)

    def read_config(self, *args, **kwargs):
        pass

    def save_config(self, message, context=None):
        pass

    def apply_config(self, responsible, paths, arg=None):
        """
        start/stop services if needed
        """
        self.generate_configfile({}) # no template variables

        context = Context.fromComponent(self)
        defer = self.core.callService(context, self.NAME, 'status')
        defer.addCallback(self._call_init_script, context)
        defer.addErrback(self.writeError)
        return defer

    def _logErr(self, fail):
        self.writeError(fail.value)

    def _call_init_script(self, (name, status), context):
        if self.is_used():
            if ServiceStatusValues.STOPPED == status:
                defer = self.core.callService(context, self.NAME, 'start')
                return defer
            elif ServiceStatusValues.RUNNING == status:
                defer = self.core.callService(context, self.NAME, 'restart')
                return defer
        else:
            if ServiceStatusValues.RUNNING == status:
                defer = self.core.callService(context, self.NAME, 'stop')
                return defer

    def is_used(self):
        """
        return True if at least one component use antivirus services
        """
        for component, is_used in self.used_by.iteritems():
            if is_used:
                return True
        return False

    # services
    def service_use(self, context, component_name, is_used):
        self.used_by[component_name] = is_used
        # no configuration for antivirus component
        # but i write some data in order to be called during apply
        with self.core.config_manager.begin(self, context) as cm:
            try:
                cm.delete(self.NAME)
            except:
                pass
            cm.set(self.NAME, self.used_by)
            cm.commit('flag antivirus config')
    # ... services

