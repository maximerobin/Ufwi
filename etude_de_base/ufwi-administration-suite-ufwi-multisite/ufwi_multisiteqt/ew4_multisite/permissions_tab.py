
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

from multisite_tab import MultisiteTab

class PermissionsTab(MultisiteTab):

    ROLES = []
    LOCAL_ROLES = ['multisite_admin']
    def __init__(self, main_window):
        self.app = None
        self.main_window = main_window
        try:
            # Start the application
            from console_edenwall.main_window import APPLICATIONS
            eas_window = main_window.eas_window
            if 'ufwi_rpcd_multisite' not in APPLICATIONS.keys():
                eas_window.init_app(APPLICATIONS['ufwi_rpcd_admin'], False)
                self.app = eas_window.apps['ufwi_rpcd_admin']
                eas_window.configure_app(self.app, APPLICATIONS['ufwi_rpcd_admin'])
                eas_window.load_app('ufwi_rpcd_admin')

            main_window.ui.perms_layout.addWidget(self.app)
        except ImportError:
            print "Please install EAS to get the Permissions tab"
