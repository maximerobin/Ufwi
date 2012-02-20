# -*- coding: utf-8 -*-

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


from ufwi_rpcd.common.abstract_cfg import AbstractConf

class HttpOutConf(AbstractConf):
    """
    configuration for httpout component.
    """
    ATTRS = """
        use_proxy
        host
        port
        user
        password
        """.split()

    DATASTRUCTURE_VERSION = 1

    def __init__(self, use_proxy=False, host='', port=3128, user='',
                 password=''):
        AbstractConf.__init__(self)
        self._setLocals(locals())

    @staticmethod
    def defaultConf():
        """
        create an empty object
        """
        use_proxy = False
        return HttpOutConf(
            use_proxy,
            '',
            3128,
            '',
            ''
            )

    def isValidWithMsg(self):
        return True, ''

    def setHost(self, host):
        self.host = unicode(host)

    def setPassword(self, password):
        self.password = unicode(password)

    def setPort(self, port):
        self.port = unicode(port)

    def setUseProxy(self, use_proxy):
        self.use_proxy = use_proxy

    def setUser(self, user):
        self.user = unicode(user)

