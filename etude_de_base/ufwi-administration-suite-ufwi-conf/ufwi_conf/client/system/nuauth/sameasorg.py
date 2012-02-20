#coding: utf8

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
from ufwi_conf.client.qt.message_area import MessageArea
from ufwi_conf.common.user_dir import SameAsOrgAuth
from ufwi_conf.common.user_dir import KerberosADAuth

from .directory_widget import DirectoryWidget

class AbstractSameAsOrg(DirectoryWidget):
    def __init__(self, config, specific_config, mainwindow, description, parent=None):
        DirectoryWidget.__init__(self, config, specific_config, mainwindow, parent=parent)
        self.__setupgui(description)

    def updateView(self, config=None):
        pass

    def __setupgui(self, description):
        msg = MessageArea()
        msg.setMessage(
            tr('About this authentication method'),
            description,
            'info'
            )

        msg.setWidth(65)
        self.form.addRow(msg)


class SameAsOrgAuthWidget(AbstractSameAsOrg):
    def __init__(self, config, specific_config, mainwindow, parent=None):
        description = tr(
            "Users are authenticated against the same server used "
            "for organizational information retrieval (see the Groups tab). "
            "Passwords are fetched through the corresponding native method."
            )
        AbstractSameAsOrg.__init__(self, config, specific_config, mainwindow, description, parent=parent)
        assert isinstance(specific_config, SameAsOrgAuth), \
            "SameAsOrgAuthWidget can only handle SameAsOrgAuth, " \
            "but got:" + type(specific_config)

class KerberosAdWidget(AbstractSameAsOrg):
    def __init__(self, config, specific_config, mainwindow, parent=None):
        description = tr(
            "Users are authenticated against the same Active Directory server used "
            "for organizational information retrieval (see the Groups tab). "
            "Authentication uses Kerberos tokens."
            )
        AbstractSameAsOrg.__init__(self, config, specific_config, mainwindow, description, parent=parent)
        assert isinstance(specific_config, KerberosADAuth), \
            "KerberosAdWidget can only handle KerberosAdAuth, " \
            "but got:" + type(specific_config)
