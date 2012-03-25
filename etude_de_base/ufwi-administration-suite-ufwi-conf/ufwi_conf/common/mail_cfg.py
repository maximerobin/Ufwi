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


from ufwi_rpcd.common.abstract_cfg import AbstractConf
from ufwi_rpcd.common.validators import check_network
from ufwi_rpcd.common.validators import check_ip_or_domain

class MailConf(AbstractConf):
    """
    configuration for mail component

    admin_mail: Administrator's e-mail address
    relay_domain_in: dict( domain: ip,  )
    relay_net_out: [ net1, net2 ]
    smarthost : if empty, smarthost not enabled
    use_antivirus: true if antivirus is used
    """

    ATTRS = """
            relay_domain_in
            smarthost
            use_antivirus
            relay_net_out
            """.split()

    DATASTRUCTURE_VERSION = 1

    def __init__(self, relay_domain_in, smarthost, use_antivirus, relay_net_out):
        AbstractConf.__init__(self)
        self._setLocals(locals())

    @staticmethod
    def defaultConf():
        """
        create an empty object
        """
        return MailConf({}, '', False, [])

    def isValidWithMsg(self):
        return self.isValid()

    def isValid(self):
        for attr in self.__class__.ATTRS:
            if getattr(self, attr) is None:
                return False, "%s is unset" % attr

        for net in self.relay_net_out:
            if not check_network(net):
                return False, "'%s' is not a valid network" % net

        if self.smarthost and not check_ip_or_domain(self.smarthost):
            return False, 'smarthost is not a valid fully qualified domain name'

        # TODO
        #for domain, ip in self.relay_domain_in.items():

        return True, ''

