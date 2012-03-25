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
from ufwi_rpcd.common.abstract_cfg import AbstractConf

class AntispamConf(AbstractConf):
    """
    configuration for antispam component
    """

    ATTRS = """
            use_antispam
            mark_spam_level
            deny_spam_level
           """.split()

    DATASTRUCTURE_VERSION = 1

    def __init__(self, use_antispam, mark_spam_level, deny_spam_level):
        AbstractConf.__init__(self)
        self._setLocals(locals())

    @staticmethod
    def defaultConf():
        """
        create an empty object
        """
        return AntispamConf(False, 5.0, 8.0)

    def isValid(self):
        for attr in self.__class__.ATTRS:
            if getattr(self, attr) is None:
                return False, tr("%(VALUE)s is unset") % {"VALUE": attr}

        for (level, message) in [(self.mark_spam_level, 'Invalid mark spam level'), (self.deny_spam_level, tr('Invalid deny spam level'))]:
            if level is None:
                return False, message

            try:
                float(level)
            except:
                return False, message

        return True, ''

