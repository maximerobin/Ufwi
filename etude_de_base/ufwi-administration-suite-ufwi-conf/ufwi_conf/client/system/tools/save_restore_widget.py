#coding: utf-8

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

from datetime import datetime
from os import strerror
from os.path import expanduser
from os.path import split
from os.path import join

from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QDialog, QFileDialog, QGroupBox, QHBoxLayout,\
         QIcon, QMessageBox, QPushButton

from ufwi_rpcd.common.download import encodeFileContent, decodeFileContent
from ufwi_rpcd.common import tr
from ufwi_rpcd.common.tools import toUnicode
from ufwi_rpcc_qt.splash import SplashScreen
from ufwi_rpcc_qt.colors import COLOR_CRITICAL, COLOR_ERROR, COLOR_FANCY, COLOR_SUCCESS
from ufwi_conf.client.qt.upload_dialog import UploadDialog

from restore_confirm_dialog import RestoreConfirmDialog
from restart_message import restoration_restart

class SaveRestoreWidget(QGroupBox):
    last_save_position = expanduser('~')

    def __init__(self, mainwindow, parent=None):
        QGroupBox.__init__(self, parent)
        self.mainwindow = mainwindow

        self.buildGui()

    def buildGui(self):
        self.__splash = SplashScreen()
        vbox = QHBoxLayout(self)
        self.setTitle(
            tr("Appliance restoration system")
        )

        save = QPushButton(
            QIcon(":/icons/down"),
            tr("Download appliance configuration"),
            self
            )
        restore = QPushButton(
            QIcon(":/icons/up"),
            tr("Restore a previously saved configuration"),
            self
        )

        for item in save, restore:
            vbox.addWidget(item)
        self.mainwindow.writeAccessNeeded(restore)

        self.connect(restore, SIGNAL('clicked()'), self.upload_file)
        self.connect(save, SIGNAL('clicked()'), self.download_file)
#        restore.setEnabled(False)

    def _start_splash(self, message):
        self.__splash.setText(tr('Please wait...'))
        self.mainwindow.addToInfoArea(message, category=COLOR_FANCY)
        self.__splash.show()

    def _stop_splash(self):
        self.__splash.hide()

    def upload_file(self):
        dialog = RestoreConfirmDialog()
        accept = dialog.exec_()
        if not accept:
            return

        dialog = UploadDialog(
            selector_label=tr("Select an EdenWall archive"),
            filter=tr("EdenWall archive (*.tar.gz *)")
            )
        accepted = dialog.exec_()

        if accepted != QDialog.Accepted:
            return

        filename = dialog.filename

        if not filename:
            return
        with open(filename, 'rb') as fd:
            content = fd.read()

        content = encodeFileContent(content)

        self.mainwindow.addToInfoArea(tr('Uploading of an archive file to restore the appliance'))
        async = self.mainwindow.client.async()
        async.call("nurestore", "restore", content,
            callback = self.success_upload,
            errback = self.error_upload
            )
        self._start_splash(tr("Uploading EdenWall restoration archive..."))

    def success_upload(self, value):
        self._stop_splash()
        message = tr("Successfully uploaded the archive file.")
        self.mainwindow.addToInfoArea(message, COLOR_SUCCESS)
        restoration_restart(self.mainwindow)

    def error_upload(self, value):
        self._stop_splash()
        message = tr("Error restoring appliance: ")
        self.mainwindow.addToInfoArea(message + unicode(value), COLOR_ERROR)

    def download_file(self):
        async = self.mainwindow.client.async()
        async.call("nurestore", "export",
            callback = self.success_download,
            errback = self.error_download
            )
        self._start_splash(tr("Downloading EdenWall restoration archive..."))

    def success_download(self, value):
        self._stop_splash()
        encoded, components = value
        self.mainwindow.addToInfoArea(tr("Downloaded EdenWall configuration"))

        extension = "*.tar.gz"
        archive_description = tr("Edenwall archive file")
        filter = "%s (%s)" % (archive_description, extension)

        date = datetime.now().strftime('%c')
        date = toUnicode(date)
        date = date.replace('.', '')
        date = date.replace(' ', '_')
        date = date.replace(':', '-')

        host = self.mainwindow.client.host
        host = host.replace('.', '_')
        host = host.replace(':', '-')
        suggestion = u"edenwall-config-%s-%s.tar.gz" % (
                host,
                date
                )

        filename = QFileDialog.getSaveFileName(
            self,
            tr("Choose a filename to save under"),
            join(SaveRestoreWidget.last_save_position, suggestion),
            filter,
            )

        filename = unicode(filename)

        if not filename:
            self.mainwindow.addToInfoArea(tr("EdenWall configuration save cancelled"))
            return

        SaveRestoreWidget.last_save_position = split(filename)[0]

        try:
            with open(filename, 'wb') as fd:
                fd.write(
                    decodeFileContent(encoded)
                    )
        except IOError, err:
            message_vars = (
                tr("An error occured while saving EdenWall configuration:"),
                toUnicode(strerror(err.errno))
                )

            text_message = "%s\n%s" % message_vars
            self.mainwindow.addToInfoArea(text_message, category=COLOR_ERROR)

            html_message = "<span>%s<br/><b>%s</b></span>" % message_vars
            QMessageBox.critical(
                self,
                tr("Save error"),
                html_message
            )
            return

        self.mainwindow.addToInfoArea(
            tr("Saved EdenWall configuration as %(filename)s") %
            {'filename': filename})


    def error_download(self, value):
        self._stop_splash()
        self.mainwindow.addToInfoArea(
            tr("An error occured while downloading EdenWall configuration: %s" % unicode(value)),
            category=COLOR_CRITICAL)

