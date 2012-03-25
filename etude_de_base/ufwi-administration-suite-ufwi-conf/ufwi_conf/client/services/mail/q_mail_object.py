
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

from ufwi_conf.common.mail_cfg import MailConf

from ufwi_conf.client.qt import QConfigObject

class QMailObject(QConfigObject):

    def __init__(self, parent=None):
        QConfigObject.__init__(self, MailConf.deserialize, 'mailcfg',
                               'setMailConfig', parent=parent)

    @classmethod
    def getInitializedInstance(cls, client):
        instance = cls.getInstance()

        if not instance.has_data():
            instance.mailcfg = client.call('exim', 'getMailConfig')
        return instance

    def has_data(self):
        return self.cfg is not None
