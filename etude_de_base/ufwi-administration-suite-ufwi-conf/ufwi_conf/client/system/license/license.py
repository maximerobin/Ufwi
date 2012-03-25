# -*- coding: utf-8 -*-
"""
$Id$
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

from os.path import basename
from PyQt4.QtCore import QCoreApplication, Qt
from PyQt4.QtGui import QAbstractItemView
from PyQt4.QtGui import QDialog
from PyQt4.QtGui import QFileDialog
from PyQt4.QtGui import QFrame
from PyQt4.QtGui import QHeaderView
from PyQt4.QtGui import QIcon
from PyQt4.QtGui import QLabel
from PyQt4.QtGui import QTableWidget, QTableWidgetItem
from PyQt4.QtGui import QVBoxLayout

from ufwi_rpcd.client.error import RpcdError
from ufwi_rpcd.common.download import encodeFileContent
from ufwi_rpcd.common.error import exceptionAsUnicode
from ufwi_rpcd.common import EDENWALL
from ufwi_rpcd.common import tr
from ufwi_rpcc_qt.colors import COLOR_CRITICAL, COLOR_ERROR
from ufwi_conf.client import NuConfPageKit
from ufwi_conf.client.qt.message_area import MessageArea
from ufwi_conf.client.qt.ufwi_conf_form import NuConfModuleDisabled
from ufwi_conf.client.qt.widgets import ScrollArea
from ufwi_conf.client.system.Update import NumberItem
if EDENWALL:
    from ufwi_conf.common.license import (option_decode,
        DPI_OPTION_NAME, INDEX_DAYS_LEFT, INDEX_OPTION, INDEX_VALIDITY)
translate = QCoreApplication.translate

class LicenseFrontend(ScrollArea):
    COMPONENT = 'license'
    LABEL = tr('Activation keys')
    REQUIREMENTS = ('license',)
    ICON = ':/icons/add_new_key.png'

    def __init__(self, client, parent):
        ScrollArea.__init__(self)
        if not EDENWALL:
            message_area = MessageArea()
            message_area.critical(
                "nuFirewall",
                tr(
                    "This EAS version does not support the Activation Key frontend but it seems that your appliance does. "
                    "Please check if another EAS version is available."
                    )
                    )
            self.setWidget(message_area)
            return
        self.client = client
        self.mainwindow = parent
        self._modified = False
        self.error_message = ''
        self._not_modifying = True
        try:
            self.ID = self.client.call("license", 'getID')
        except RpcdError:
            self.__disable("Could not fetch activation key info")

        self.buildInterface()
        self.getValidLicenses()

    @staticmethod
    def get_calls():
        """
        services called by initial multicall
        """
        return (("license", 'getID'),)

    def __disable(self, reason):
        self.mainwindow.addToInfoArea(
            tr("The activation key management interface is disabled."),
            COLOR_ERROR
            )
        self.mainwindow.addToInfoArea(
            reason,
            COLOR_ERROR
            )
        self.close()
        raise NuConfModuleDisabled(reason)

    def buildInterface(self):
        frame = QFrame()
        layout = QVBoxLayout(frame)
        self.setWidget(frame)
        self.setWidgetResizable(True)

        title = u'<h1>%s</h1>' % self.tr('EdenWall activation keys')
        layout.addWidget(QLabel(title))

        sn = "<strong>%s</strong>" % self.ID
        self.IDLabel = QLabel(tr('This appliance serial number is %s.') % sn)
        self.IDLabel.setTextInteractionFlags(
            Qt.TextSelectableByKeyboard | Qt.TextSelectableByMouse)
        sendLicenseButton = NuConfPageKit.createButton(
            tr('Upload an activation key'), frame, self.mainwindow,
            self.chooseAndSendFile, QIcon(":/icons/up"))
        self.mainwindow.writeAccessNeeded(sendLicenseButton)

        self.table = QTableWidget(0, 4, frame)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setResizeMode(QHeaderView.ResizeToContents)
        self.table.setHorizontalHeaderLabels([
                unicode(translate('MainWindow', 'Activation key owner')),
                unicode(translate('MainWindow', 'Valid until')),
                unicode(translate('MainWindow', 'Days left')),
                unicode(translate('MainWindow', 'Type'))])

        for widget in (self.IDLabel, sendLicenseButton, self.table):
            layout.addWidget(widget)
        layout.addStretch(100)

    def developOptions(self, licenses):
        """Return a list of licenses with only one option each."""
        developpedOptions = []
        for license in licenses:
            for option in license[INDEX_OPTION].split():
                developpedOption = license[:]
                developpedOption[INDEX_OPTION] = option
                if option == DPI_OPTION_NAME:
                    developpedOption[INDEX_VALIDITY] = "unlimited"
                    developpedOption[INDEX_DAYS_LEFT] = ""
                developpedOptions.append(developpedOption)
        return developpedOptions

    def getValidLicenses(self):
        """Display valid licenses in the table."""
        try:
            licenses = self.client.call("license", 'getValidLicenses')
        except RpcdError, err:
            licenses = []
            self.mainwindow.addToInfoArea(exceptionAsUnicode(err),
                                          category=COLOR_CRITICAL)
        developpedOptions = self.developOptions(licenses)
        self.table.setRowCount(len(developpedOptions))
        for row, developpedOption in enumerate(developpedOptions):
            for col, item in enumerate(developpedOption):
                if col == INDEX_DAYS_LEFT:
                    self.table.setItem(row, col, NumberItem(unicode(item)))
                else:
                    self.table.setItem(row, col,
                        QTableWidgetItem(option_decode(unicode(item))))

    def pleaseRestartEASDialog(self, need_ufwi_rpcd_restart=False):
        dialog = QDialog(self)
        dialog.setModal(False)
        if need_ufwi_rpcd_restart:
            title = tr("Please restart the configuration service and EAS")
            msg = tr("Please restart the configuration service, then "
                     "EAS to use unlocked functionalities.")
        else:
            title = tr("Please restart EAS")
            msg = tr("Please restart EAS to use unlocked functionalities.")
        dialog.setWindowTitle(title)
        label = NuConfPageKit.createLabel(msg, dialog)

        layout = QVBoxLayout(dialog)
        dialog.setLayout(layout)
        button = NuConfPageKit.createButton(translate('MainWindow', 'Close'),
                                            dialog, dialog, dialog.close)
        for widget in (label, button):
            layout.addWidget(widget)
            widget.show()
        dialog.show()

    # Slots:
    def chooseAndSendFile(self):
        filename = unicode(
            QFileDialog.getOpenFileName(self.mainwindow,
                translate('MainWindow',
                          'Select the EdenWall activation key file to upload')))
        if not filename:
            return

        basefilename = basename(filename)
        with open(filename, 'rb') as fd:
            content = fd.read()
        try:
            minimalmode = self.client.call('acl', 'getMinimalMode')
            if self.client.call('license', 'sendLicense',
                                encodeFileContent(content)):
                self.mainwindow.addToInfoArea(translate('MainWindow',
                    "Uploaded activation key file") + " `%s'." % basefilename)
                try:
                    need_ufwi_rpcd_restart = self.client.call(
                        "license", "needNucentralRestart")
                except Exception:
                    need_ufwi_rpcd_restart = False
                if need_ufwi_rpcd_restart:
                    self.mainwindow.addToInfoArea(
                        tr("You need to restart the configuration "
                           "service and EAS to use the protocol analysis "
                           "configuration service"))
                if need_ufwi_rpcd_restart or (
                    minimalmode and not self.client.call('acl',
                                                         'getMinimalMode')):
                    self.pleaseRestartEASDialog(need_ufwi_rpcd_restart)
            else:
                self.mainwindow.addToInfoArea(translate('MainWindow',
                    "No new activation key for this appliance in this file."))
        except RpcdError, err:
            self.mainwindow.addToInfoArea(translate('MainWindow',
                "Error while uploading activation key file") + " `%s': %s" %
                (basefilename, exceptionAsUnicode(err)), category=COLOR_CRITICAL)
        self.getValidLicenses()

    def isModified(self):
        return False
