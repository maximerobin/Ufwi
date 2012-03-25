
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

import os
from shutil import copy2

FACTORY_MENU_LST = '/usr/share/ufwi_rpcd/templates/boot/grub/factory_menu.lst'
MENU_LST = '/boot/grub/menu.lst'
PROD_MENU_LST = '/boot/grub/prod_menu.lst'

def askFactoryDefault():
    if not is_factory_default_asked():
        copy2(MENU_LST, PROD_MENU_LST)
        copy2(FACTORY_MENU_LST, MENU_LST)
        return True
    return False

def is_factory_default_asked():
    with open(FACTORY_MENU_LST) as fd:
        factory_menu_lst_contents = fd.read()
    with open(MENU_LST) as fd:
        menu_lst_contents = fd.read()
    return factory_menu_lst_contents == menu_lst_contents

def cancel_factory_default():
    if not os.path.exists(PROD_MENU_LST):
        return False
    copy2(PROD_MENU_LST, MENU_LST)
    return True
