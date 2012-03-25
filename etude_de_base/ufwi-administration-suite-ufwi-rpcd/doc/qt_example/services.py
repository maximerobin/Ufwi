
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

from nucentral.qt.tools import QComboBox_setCurrentText
from PyQt4.QtCore import SIGNAL, QObject

class Services(QObject):
    def __init__(self, window):
        QObject.__init__(self)
        self.window = window
        self.client = window.client
        self.service_list = window.service_list
        self.component_combo = window.component_combo
        self.documentation_button = window.documentation_button

        self.connectSignals()
        self.fillComponents()
        QComboBox_setCurrentText(self.component_combo, "CORE")

    def connectSignals(self):
        window = self.window
        window.connect(
            self.component_combo,
            SIGNAL("currentIndexChanged(int)"),
            self.fillServices)
        window.connect(
            window.service_list.selectionModel(),
            SIGNAL("selectionChanged(QItemSelection, QItemSelection)"),
            self.selectService)
        window.connect(
            self.documentation_button,
            SIGNAL("clicked()"),
            self.showDocumentation)

    def fillComponents(self):
        components = self.client.call('CORE', 'getComponentList')
        self.component_combo.clear()
        self.component_combo.addItems(components)

    def currentComponent(self):
        return unicode(self.component_combo.currentText())

    def currentService(self):
        item = self.service_list.currentItem()
        if not item:
            return None
        return unicode(item.text())

    def fillServices(self):
        component = self.currentComponent()
        self.service_list.clear()
        services = self.client.call('CORE', 'getServiceList', component)
        for service in services:
            self.service_list.addItem(service)
        self.selectService(tuple(), tuple())

    def showDocumentation(self):
        component = self.currentComponent()
        service = self.currentService()
        if not service:
            return
        doc = self.client.call('CORE', 'help', component, service)
        if doc:
            doc = u'\n'.join(doc)
        else:
            doc = u"(no documentation)"
        self.window.information(doc)

    def selectService(self, selected, deselected):
        enabled = bool(selected)
        self.documentation_button.setEnabled(enabled)

