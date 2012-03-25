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
from ufwi_rpcd.common.validators import check_mail

class ContactConf(AbstractConf):
    """
    configuration for contact component

    admin_mail: Administrator's e-mail address
    sender_mail
    """

    ATTRS = """
            admin_mail
            sender_mail
            language
            """.split()

    DATASTRUCTURE_VERSION = 1

    CODE_TO_NAME = {'en':'English', 'fr':u'Français'}

    def __init__(
        self, admin_mail='',
        sender_mail='',
        language='en',
        ):
        AbstractConf.__init__(self)
        self._setLocals(locals())

    @staticmethod
    def defaultConf():
        """
        create an empty object
        """
        return ContactConf()

    def isValidWithMsg(self, allow_empty=True):
        for attr in self.__class__.ATTRS:
            if getattr(self, attr) is None:
                return False, "%s is unset" % attr

        if self.language not in ['en', 'fr']:
            return False, "unknow language '%s'" % self.language

        if not(allow_empty and 0 == len(self.admin_mail)):
            if not check_mail(self.admin_mail):
                return False, 'Administrator e-mail is invalid'

        if not(allow_empty and 0 == len(self.sender_mail)):
            if not check_mail(self.sender_mail):
                return False, 'sender e-mail is invalid'

        return True, ''

