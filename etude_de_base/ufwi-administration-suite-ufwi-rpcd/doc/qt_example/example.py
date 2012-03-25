#!/usr/bin/env python
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


from nucentral.qt.application import create_nucentral_application
from sys import exit

def main():
    app, client = create_nucentral_application(
        name="example",
        resource="example.rcc",
        locale=":/locale/example",
    )

    from main_window import MainWindow
    window = MainWindow(client)
    window.show()
    return app.exec_()

if __name__ == "__main__":
    code = main()
    exit(code)

