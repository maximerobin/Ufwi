# -*- coding: utf-8 -*-
"""
Copyright (C) 2008-2011 EdenWall Technologies
Written by Feth AREZKI <farezki AT edenwall.com>

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
from ufwi_conf.backend.unix_service import ConfigServiceComponent

class QuaggaComponent(ConfigServiceComponent):
    NAME = "quagga"
    VERSION = "1.0"

    REQUIRES = ()

    INIT_SCRIPT = "/bin/true"

    ROLES = { }

    ACLS = { }

    CONFIG_DEPENDS = ()

    def __init__(self):
        ConfigServiceComponent.__init__(self)

    def init(self, core):
        ConfigServiceComponent.init(self, core)

    def read_config(self, *args, **kwargs):
        pass

    def apply_config(self, *unused):
        pass

    def service_runtimeFiles(self, context):
        return  {
            'deleted': (),
            'added' : (('/etc/quagga', 'dir'),)
            }

    def service_runtimeFilesModified(self, context):
        #FIXME: reload the files :)
        self.info("* Quagga component cannot reload its runtime files yet *")

