
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
from os.path import join
from twisted.internet.defer import inlineCallbacks

from ufwi_rpcd.common import EDENWALL
from ufwi_rpcd.common.service_status_values import ServiceStatusValues
from ufwi_rpcd.core.context import Context
from ufwi_rpcd.backend import Component

from ufwi_conf.backend.ufwi_conf_component import AbstractNuConfComponent
from ufwi_conf.common.system_info import FIREWALL_MODELS, EMS, EMI

"""
sample /var/lib/ufwi_rpcd/licence.txt
client Client not specified
model Edenwall500
hw_version 0.99
"""

ALLOWED_MODELS = set(FIREWALL_MODELS + [EMS, EMI])
HW_VERSION_FILENAME = '/var/lib/ufwi_rpcd/hw_version'

class SystemInfoComponent(AbstractNuConfComponent):
    NAME = "system_info"
    VERSION = "1.0"
    REQUIRES = ('license',) if EDENWALL else ()
    ACLS = {'license': set(('getLicenseInfo',))}
    ROLES = {
        'conf_read': set(("systemInfo",)),
        'multisite_read': set(("systemInfo",)),
        'multisite_write': set(("@multisite_read",)),
    }

    # TODO change the language

    def __init__(self):
        AbstractNuConfComponent.__init__(self)
        self.values = {}

    def _get_sw_version(self):
        try:
            with open('/etc/ew_version') as fp:
                line = fp.readline()
        except IOError, err:
            self.warning("Unable to read software version: %s" % err)
            return ''
        return line.rstrip()

    @inlineCallbacks
    def init(self, core):
        Component.init(self, core)
        self.core = core
        vardir = core.config.get('CORE', 'vardir')

        sw_version = self._get_sw_version()

        filename = join(vardir, 'licence.txt')
        try:
            with open(filename, 'r') as fd:
                for line in fd.readlines():
                    split = line.split()
                    key = split[0]
                    try:
                        value = " ".join(split[1:])
                    except IndexError:
                        self.fail("check %s" % filename)
                    self.values[key] = value
        except IOError, err:
            #TODO: reenable this
            #self.fail("could not read %s" % filename)
            #TODO: remove this
            self.values = {
                "sw_version": sw_version,
            }
            if EDENWALL:
                self.values.update(
                    {
                    "client": "Client not specified",
                    "model": "EW4",
                    "type": "EW4",   # For compatibility with old EAS.
                    "hw_version": "4.2.1",
                    "serial": "000000000000000"
                    }
                )
        if EDENWALL:
            try:
                with open(HW_VERSION_FILENAME) as fd:
                    self.values['hw_version'] = fd.read().strip()
            except Exception:
                self.warning('No hardware version information.')

            try:
                yield self.getLicenseInfo()
                self.check()
            except Exception, fail:
                self.writeError(fail, "Unable to get license info")

    @inlineCallbacks
    def getLicenseInfo(self):
        ctx = Context.fromComponent(self)
        info = yield self.core.callService(ctx, 'license', 'getLicenseInfo')

        model = info.get('model', '')
        ID = info.get('ID', '')
        owner = info.get('owner', '')

        self.values['model'] = model
        self.values['serial'] = ID
        self.values['client'] = owner
        # For compatibility with old EAS.
        self.values['type'] = model

    def check(self):
        if not EDENWALL:
            return
        read_model = self.values.get('model', '')
        if read_model in ALLOWED_MODELS:
            return
        #TODO: reenable this
        #self.fail("invalid edenwall model %s" % read_model)
        #TODO: remove this
        self.error("invalid edenwall model %s" % read_model)

    def fail(self, message):
        self.critical(message)
        self.core.exit(1)

    def read_config(self, *args, **kwargs):
        pass

    def save_config(self, message=None, context=None):
        pass

    def _update(self):
        sw_version = self._get_sw_version()
        if sw_version:
            self.values['sw_version'] = sw_version

    def service_systemInfo(self, context):
        self._update()
        return self.values

    def service_status(self, context):
      """
      Implementation compulsory because NOT_A_SERVICE
      is not expected from a UnixServiceComponent
      """
      return self.NAME, ServiceStatusValues.NOT_A_SERVICE
