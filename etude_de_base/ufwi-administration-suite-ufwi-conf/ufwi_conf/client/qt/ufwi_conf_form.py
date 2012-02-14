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


from PyQt4.QtGui import (QDialog, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget)
from PyQt4.QtCore import QCoreApplication, SIGNAL, SLOT, QString
translate = QCoreApplication.translate
from logging import error

from ufwi_rpcd.client import RpcdError
from ufwi_rpcd.common import tr

from ufwi_conf.client.NuConfWidgets import ListSectionWidget
from ufwi_conf.client.NuConfPageKit import (BUTTON_IDX, INPUT_IDX, createButton,
    createPageLabel, createLabelAndCheckBox, createLabelAndLineEdit)
from ufwi_conf.client.NuConfValidators import (hostOrIpValidator,
    hostIPValidator, hostnameValidator, netNameValidator, proxyValidator)
from ufwi_conf.client.qt.base_widget import BaseWidget

type2validator = {
    'hostOrIp' : hostOrIpValidator,
    'hostIp': hostIPValidator,
    'hostname': hostnameValidator,
    'domainname': netNameValidator,
    'proxy': proxyValidator,
    }

class NuConfModuleDisabled(Exception):
    pass

class NuConfForm(QWidget, BaseWidget):
    def __init__(self, main_window, name_path, name, displayBottomButtons=True):
        BaseWidget.__init__(self)

        self.component = self.COMPONENT

        self.main_window = main_window

        self.InfoArea = main_window.InfoArea
        self.client = main_window.client
        #self.item = item
        self.displayBottomButtons = displayBottomButtons
        self.displayBottomButtons = False
        # Variable naming convention tip: "control" should always refer to a
        # structure from the menu (a dictionary), and "ctl" to a custom
        # structure containing a control, along with other data like widgets.
        self.ctls = []
        self.errors = []
        QWidget.__init__(self, None)

        self.check_module_disabled()

        self.loadConf()
        self.setObjectName('form')
        self.layout = QVBoxLayout(self)
        self.layout.setObjectName('formLayout')
        self.layout.setMargin(9)
        self.layout.setSpacing(6)
        self._modified = False

        # Label (name of the page):
        self.name = name
        page_name = self.translatePath(name_path, name)
        self.layout.addWidget(createPageLabel(page_name))


        # Main (specific) part:
        scrollWidget, scrollLayout = self._createScrollArea()
        self.createForm(scrollWidget, scrollLayout)


        # Buttons at the bottom of the page:
        if self.displayBottomButtons:
            self.layout.addWidget(self.createBottomButtons())

        self.setLayout(self.layout)

        self.excToErrorMessage = {'[DhcpError] Wrong order': translate('MainWindow',
                    'DHCP server settings: the end IP address must be ' +
                    'greater than the start IP address.'),
                    }

        self.resetConf()

    @staticmethod
    def get_calls():
        return ( ('CORE', 'getComponentList'), )

    def check_module_disabled(self):
        componentList = self.main_window.init_call('CORE', 'getComponentList')
        for c in self._get_component_list():
            if not c in componentList:
                error("Missing component: %s" % c)
                raise NuConfModuleDisabled


    def isModified(self):
        return self._modified

    def translatePath(self, name_path, item_name):
        if not name_path:
            return item_name
        else:
            separator = tr(': ')
            result = QString()
            for name in name_path:
                result += tr(name) + separator
            return result + tr(item_name)

    def _createScrollArea(self):
        scrollArea = QScrollArea(self)
        scrollArea.setObjectName('scrollArea')
        scrollArea.setWidgetResizable(True)
        scrollWidget = QWidget(scrollArea)
        scrollWidget.setObjectName('scrollWidget')
        scrollArea.setWidget(scrollWidget)
        scrollLayout = QVBoxLayout(scrollWidget)
        scrollLayout.setObjectName('scrollLayout')
        self.layout.addWidget(scrollArea)
        return scrollWidget, scrollLayout

    def createBottomButtons(self):
        bottom = QWidget(self)
        bottom_layout = QHBoxLayout()
        bottom_layout.setObjectName('bottomLayout')
        bottom.setLayout(bottom_layout)
        buttons = (
            createButton(tr('&Save'),
                bottom, self.main_window, self.checkAndSaveConf),
            createButton(tr('App&ly'),
                bottom, self.main_window, self.applyConf),
            createButton(tr('Reset'),
                bottom, self.main_window, self.resetConf),
            )
        for button in buttons:
            bottom_layout.addWidget(button)
        return bottom

    def addError(self, exc):
        text = self.excToErrorMessage.get(unicode(exc), unicode(exc))
        self.errors.append(text)
        self.InfoArea.insertHtml(
                '%s<span style="color: red;">%s</span><br/><br/>' %
                (self.main_window.getTimestamp(), text))

    def addErrorIfAny(self, subject, msg=''):
        if msg is not None:
            if subject in self.errors:
                self.errors[subject].append(msg)
            else:
                self.errors[subject] = [msg]
            return True
        return False

    def showErrors(self, intro = None):
        if not self.errors:
            return
        dialog = QDialog(self.main_window)
        dialog.setObjectName('errorDialog')
        dialog.setWindowTitle(tr('Error(s)'))
        layout = QVBoxLayout(dialog)
        dialog.setLayout(layout)
        if intro != '':
            if intro is None:
                intro = translate('MainWindow',
                    'Some errors were found in this form:')
            label = QLabel(intro)
            layout.addWidget(label)
        for subject, messages in self.errors.items():
            for msg in messages:
                if msg:
                    label = QLabel('- %s%s%s' % (subject,
                        unicode(tr(': ')),
                        unicode(msg)))
                else:
                    label = QLabel('- %s' % unicode(subject))
                layout.addWidget(label)
        button = createButton(translate('MainWindow',
            'Edit again'), dialog, dialog, SLOT('close()'))
        layout.addWidget(button)
        dialog.exec_()

    def createForm(self, page, layout):
        layout.addStretch(100)
        # since creating the form change the needed module
        # we should check again that nothing more is needed
        # this is a hack and should be corrected
        self.check_module_disabled()

        return self

    def controlToWidget(self, control):
        wid = None
        type_ = control['type']
        if type_ == 'enable':
            wid, input_wid = createLabelAndCheckBox(
                    tr(control['label']),
                    self.stateChanged)
        elif type_ == 'hostIpList':
            wid = ListSectionWidget(self, [], hostIPValidator)
            self.connect( wid, SIGNAL("itemToAdd"), lambda: self.addIp(wid))
            self.connect( wid, SIGNAL("itemToDelete"), lambda col: self.deleteIp(wid, col))

            input_wid = None
        else:  # Label and LineEdit types:
            wid, label, input_wid = createLabelAndLineEdit(
                    tr(control['label']),
                    self.stateChanged, type2validator.get(type_, None))
        if wid:
            self.ctls.append((control, wid, input_wid))
        return wid

    # TODO more check
    def addIp(self, wid):
        ip = wid.getInputText()
        wid.addRowList(ip)

    def deleteIp(self, wid, col):
        wid.deleteRowList(col)

    def setModified(self, modified=True):
        if self._modified == modified:
            return
        self._modified = modified
        self.main_window.setModified(self, modified)

    def loadConf(self):
        pass

    def checkConf(self):
        text = tr('Checking view ') + \
            tr(self.name)
        self.setStatus(text)
        self.main_window.addToInfoArea(text)
        # First, send the new data to the backend (stored in RAM):
        for ctl in self.ctls:
            control, wid, input_wid = ctl
            type_ = control['type']

            component = self._get_component(control)

            if type_.endswith('List'):

                clear = 'clear' + control['get/clear']
                self.client.call(component, clear)

                add = 'add' + control['add/del']
                for text in wid.getValueList():
                    self.client.call(component, add, text)

            elif type_ == 'enable':
                if input_wid.isChecked():
                    checked = 1
                else:
                    checked = 0
                self.client.call(component, 'setEnabledOnBoot', checked)

            else:
                set = 'set' + control['get/set']
                self.client.call(component, set, unicode(input_wid.text()))
        try:
            for c in self._get_component_list():
                self.client.call(c, 'checkConfiguration')
            return True
        except RpcdError, e:
            self.addError(e)
            return False

    def checkAndSaveConf(self):
        if self.checkConf():
            self.saveConf()

    def setStatus(self, status):
        self.main_window.setStatus(status, self.main_window.statusBarTimeout)

    def applyConf(self):
        # First, make sure the configuration is sane, saved and generated:
        if not self.saveConf():
            return False

        for c in self._get_component_list():
            try:
                self.client.call(c, 'restart')
            except RpcdError:
                self.setStatus( tr('Error(s) while applying the configuration.'))
                return False
            self.setStatus( tr('Configuration applied.'))
            return True
        return False

    def _get_component(self, control):
        component = self.component
        if 'component' in control:
            component = control['component']
        return component

    def _get_component_list(self):
        components = []
        if 'component' in dir(self) and self.component:
            components.append(self.component)

        if 'components' in dir(self):
            components.extend(self.components)

        for ctl in self.ctls:
            c = ctl[0]
            if 'component' in c:
                if not c['component'] in components:
                    components.append(c['component'])
        return components

    def resetConf(self):

        for c in self._get_component_list():
            self.client.call(c, 'readConfiguration')

        for ctl in self.ctls:
            control, frame, input_wid = ctl
            type_ = control['type']

            component = self._get_component(control)

            if type_.endswith('List'):
                frame.clearList()
                get = 'get' + control['get/clear']
                list = self.client.call(component, get)
                frame.setList(list)

            elif type_ == 'enable':
                if self.client.call(component, 'getEnabledOnBoot'):
                    input_wid.setChecked(True)
                else:
                    input_wid.setChecked(False)

            else:
                get = 'get' + control['get/set']
                input_wid.setText(self.client.call(component, get))

        self.setModified(False)

    # Slots:

    def cellChanged(self, row, column):
        self.setModified(True)

    def stateChanged(self, state):
        self.setModified(True)

