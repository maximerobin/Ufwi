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


from __future__ import with_statement

from os import getcwd
from PyQt4.QtCore import QCoreApplication, QObject, Qt, QTimer, SIGNAL
from PyQt4.QtCore import QString
from PyQt4.QtGui import (QAbstractItemView, QAction, QDialog,
                         QDialogButtonBox, QFileDialog, QFrame, QGridLayout,
                         QGroupBox, QHBoxLayout, QHeaderView, QIcon, QLabel,
                         QProgressBar, QPushButton, QTableWidget,
                         QTableWidgetItem, QVBoxLayout)

translate = QCoreApplication.translate
from functools import partial
from os.path import basename, dirname
from datetime import datetime

from ufwi_rpcd.common import tr
from ufwi_rpcd.common.error import exceptionAsUnicode
from ufwi_rpcd.common.download import encodeFileContent
from ufwi_rpcd.common.human import fuzzyTimedelta
from ufwi_rpcd.client.error import RpcdError
from ufwi_rpcc_qt.colors import COLOR_SUCCESS, COLOR_ERROR, COLOR_CRITICAL
from ufwi_rpcc_qt.html import htmlColor, htmlBold
from ufwi_rpcc_qt.splash import SplashScreen
from ufwi_rpcc_qt.user_settings import UserSettings

from ufwi_conf.client import NuConfPageKit
from ufwi_conf.client.qt.ufwi_conf_form import NuConfForm
from ufwi_conf.client.qt.toolbar import ToolBar
from ufwi_conf.client.qt.widgets import CenteredCheckBox
from ufwi_conf.client.system.resolv.qhostname_object import QHostnameObject
from ufwi_conf.common.update import (
    UPGRADE_STATUS_IN_PROGRESS, UPGRADE_STATUS_NEED_RESTART,
    upgrade_number)
from ufwi_conf.common.update_cfg import UpdateCfg

REFRESH_INTERVAL_MILLISECONDS = 5000
STREAMING_INTERVAL_SECONDS = 2

def utc_to_localtime(utc_datetime_string):
    """Convert a datetime from UTC to local time (see format below)"""
    import time
    format = '%Y-%m-%d %H:%M:%S'
    utc_datetime = time.mktime(time.strptime(utc_datetime_string, format))
    if time.localtime(utc_datetime)[8]:  # isdst.
        zone = time.altzone
    else:
        zone = time.timezone
    return time.strftime(format, time.localtime(utc_datetime - zone))

def unicode_join(separator, seq):
    return separator.join(unicode(el) for el in seq)

class NumberItem(QTableWidgetItem):
    def __init__(self, text):
        QTableWidgetItem.__init__(self, text)
        self.setTextAlignment(Qt.AlignRight|Qt.AlignVCenter)

def _get_directory():
    settings = UserSettings("Nuconf")
    settings.beginGroup("Update")
    result = settings.getUnicode("lastdir", getcwd())
    settings.endGroup()
    return result

def _save_directory(directory):
    settings = UserSettings("Nuconf")
    settings.beginGroup("Update")
    settings.setUnicode("lastdir", directory)
    settings.endGroup()

class Update(NuConfForm):
    COMPONENT = 'update'
    LABEL = tr('Update')
    REQUIREMENTS = ('update',)
    ICON = ':/icons/download.png'

    def __init__(self, main_window, name_path, item_name):
        self.timer = None
        self.downloading = 0
        self.previous_history = None
        self.msg_no_connection = False
        self.needRestart = ''
        self.stream_id = None
        self._previously_in_progress = False
        self.splash = SplashScreen()
        NuConfForm.__init__(self, main_window, name_path, item_name)

    @staticmethod
    def get_calls():
        """
        services called by initial multicall
        """
        return NuConfForm.get_calls() + (
            ('update', 'uploadedUpgrades'),
            ('update', 'getHighestApplied'),
            )

    # Slots:
    def applyAll(self):
        self.previous_history = self.client.call(self.component, 'history')
        if self.client.call(self.component, 'applyAll'):
            self.main_window.addToInfoArea(
                translate('MainWindow', 'Applying all updates.'))
            self.resetConf()
        else:
            self.display_update_locked()

    def applySelected(self):
        self.previous_history = self.client.call(self.component, 'history')
        if self.client.call(self.component, 'applyUpgrades',
                            self.selected.keys()):
            self.main_window.addToInfoArea(
                translate('MainWindow', 'Applying selected updates.'))
        else:
            self.display_update_locked()
        self.resetConf()

    def _uploadDone(self):
        self.splash.hide()
        try:
            blacklisted_and_present = self.client.call(
                'update', 'getBlacklistedAndPresent')
        except Exception:
            # Don't make a fuss if the backend does not have this service.
            blacklisted_and_present = []
        if blacklisted_and_present:
            if len(blacklisted_and_present) > 1:
                self.main_window.addToInfoArea(
                    tr('Deleting the following superseded updates: %s.') %
                    unicode_join(', ', blacklisted_and_present))
            else:
                self.main_window.addToInfoArea(
                    tr('Deleting superseded update %s.') %
                    blacklisted_and_present[0])
            try:
                self.client.call(self.component, 'deleteUpgradeArchives',
                                 blacklisted_and_present)
                self.deleted_superseded_dialog(blacklisted_and_present)
            except RpcdError, err:
                self.main_window.addToInfoArea(
                    tr("Error while deleting updates: %s") %
                    exceptionAsUnicode(err), category=COLOR_ERROR)
        self.resetConf()

    def uploadSuccess(self, number, start, result):
        if result >= 0:
            diff = datetime.now() - start
            message = tr("Uploaded update archive %s (%s).") \
                % (number, fuzzyTimedelta(diff))
            self.main_window.addToInfoArea(message, category=COLOR_SUCCESS)
        else:
            self.main_window.addToInfoArea(
                tr("Error while uploading archive %s.") % number,
                category=COLOR_CRITICAL)
        self._uploadDone()

    def uploadFailure(self, number, err):
        self.main_window.addToInfoArea(
            tr("Error while uploading archive %s: %s") %
            (number, exceptionAsUnicode(err)),
            category=COLOR_CRITICAL)
        self._uploadDone()

    def chooseAndSendFile(self):
        # Get filename
        open_caption = tr( 'Choose an EdenWall update archive to upload')
        open_directory = _get_directory()
        filename = unicode(
            QFileDialog.getOpenFileName(
                self.main_window,
                open_caption,
                open_directory
                )
                )
        if not filename:
            return

        # Get archive number from the filename
        basefilename = basename(filename)
        _save_directory(dirname(filename))
        number = upgrade_number(basefilename)
        if number is None:
            self.main_window.addToInfoArea(
                tr("No upgrade number found in archive file name `%s'.")
                    % basefilename,
                category=COLOR_ERROR)
            return

        message = tr("Uploading update %s...") % number
        self.main_window.addToInfoArea(message)

        # Read content and encode it to base64
        with open(filename, 'rb') as fd:
            content = fd.read()
        content_base64 = encodeFileContent(content)
        content = None

        # Display a splash screen
        self.splash.setText(message)
        self.splash.show()

        # Upload the archive...
        start = datetime.now()
        async = self.client.async()
        async.call('update', 'sendUpgradeArchive', basefilename, content_base64,
            callback = partial(self.uploadSuccess, number, start),
            errback = partial(self.uploadFailure, number),
        )

    def deleteSelected(self):
        really_deleted_nums = self.client.call(
            self.component, 'deleteUpgradeArchives', self.selected.keys())
        if self.selected:
            if really_deleted_nums == []:
                self.main_window.addToInfoArea(
                    translate('MainWindow', "All updates selected for deletion are being applied and were not deleted."))
            else:
                self.main_window.addToInfoArea(
                    translate('MainWindow', "Deleted update(s)") + (' %s.' %
                    ', '.join(unicode(num) for num in self.selected.keys())))
        else:
            self.main_window.addToInfoArea(
                translate('MainWindow', "You have not selected any update."))
        self.resetConf()

    def display_history(self):
        dialog = QDialog(self)
        dialog.setModal(False)
        title = translate('MainWindow', 'Update history')
        dialog.setWindowTitle(title)
        label = NuConfPageKit.createLabel('<h1>%s</h1>' % title, dialog)
        table = QTableWidget(0, 5, dialog)

        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.NoSelection)
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setHidden(True)
        table.setHorizontalHeaderLabels([
                unicode(translate('MainWindow', 'Number')),
                unicode(translate('MainWindow', 'Result')),
                unicode(translate('MainWindow', 'Apply date')),
                unicode(translate('MainWindow', 'Applied by')),
                unicode(translate('MainWindow', 'Changelog'))])

        history = self.client.call(self.component, 'history')
        table.setRowCount(len(history))
        for row, upgrade in enumerate(history):
            table.setItem(row, 0, NumberItem('%s' % upgrade[1]))
            if upgrade[5]:
                result = QTableWidgetItem(translate('MainWindow', 'Success'))
                result.setTextColor(Qt.darkGreen)
            else:
                result = QTableWidgetItem(translate('MainWindow', 'Failed'))
                result.setTextColor(Qt.red)
            table.setItem(row, 1, result)
            table.setItem(row, 2, NumberItem('%s' %
                                             utc_to_localtime(upgrade[6])))
            table.setItem(row, 3, QTableWidgetItem(upgrade[7]))
            table.setItem(row, 4, QTableWidgetItem(upgrade[3]))
        table.horizontalHeader().setResizeMode(QHeaderView.ResizeToContents)


        layout = QVBoxLayout(dialog)
        dialog.setLayout(layout)
        button = NuConfPageKit.createButton(translate('MainWindow', 'Close'),
                                            dialog, dialog, dialog.close)
        for widget in (label, table, button):
            layout.addWidget(widget)
            widget.show()
        dialog.resize(800, 560)
        dialog.show()

    def displayServerConf(self):
        self.dialog = QDialog(self)
        self.dialog.setModal(False)
        title = translate('MainWindow', 'Update server configuration')
        self.dialog.setWindowTitle(title)
        label = NuConfPageKit.createLabel('<h1>%s</h1>' % title, self.dialog)
        layout = QVBoxLayout(self.dialog)
        self.dialog.setLayout(layout)

        self.tmp_use_custom_mirror = self.config.use_custom_mirror
        self.tmp_auto_check = self.config.auto_check

        # Use custom mirror checkbox:
        (use_custom_mirror_check, self.use_custom_mirror_checkbox) = \
            NuConfPageKit.createLabelAndCheckBox(
            translate('MainWindow',
                      'Use a custom update mirror.'),
            self.useCustomMirrorCheck)
        self.use_custom_mirror_checkbox.setChecked(
            self.config.use_custom_mirror)

        # Update mirror line edit:
        (update_mirror_edit_widget, _, self.update_mirror_edit) = \
            NuConfPageKit.createLabelAndLineEdit(
            translate('MainWindow', 'Update mirror URL'), None)
        self.update_mirror_edit.setText(self.config.update_mirror)

        # Auto check checkbox:
        (update_server_check, self.update_server_checkbox) = \
            NuConfPageKit.createLabelAndCheckBox(
            translate('MainWindow',
                      'Enable automatic checking of new updates.'),
            self.updateServerCheck)
        self.update_server_checkbox.setChecked(self.config.auto_check)

        # Button box:
        button_box = QDialogButtonBox()
        button_box.setStandardButtons(QDialogButtonBox.Cancel |
                                      QDialogButtonBox.Ok)
        self.main_window.connect(button_box, SIGNAL('accepted()'),
                                 self.saveAndCloseServerConf)
        self.main_window.connect(button_box, SIGNAL('rejected()'),
                                 self.dialog.close)

        for widget in (label, use_custom_mirror_check,
                       update_mirror_edit_widget, update_server_check,
                       button_box):
            layout.addWidget(widget)
            widget.show()
        self.dialog.show()

    def _downloadFinished(self):
        self.streaming_unsubscribe(self.stream_id)
        self.main_window.addToInfoArea(
            translate('MainWindow', 'Finished downloading new updates.'),
            category=COLOR_SUCCESS)

    def downloadNewUpgrades(self):
        def success_callback(unused):
            streaming = self.client.streaming()
            if streaming is not None:
                self.stream_id = streaming.subscribe(
                    self.downloadProgress, STREAMING_INTERVAL_SECONDS,
                    self.component, 'getDownloadProgress', ())
            else:
                counts = self.client.call(self.component,
                                          "getDownloadProgress")
                if counts[3]:
                    self.main_window.addToInfoArea(translate(
                            'MainWindow', 'Error while downloading new updates: '
                            ) + counts[3], category=COLOR_CRITICAL)
                    self.updateDownloadBar(counts)
                elif not int(counts[2]):
                    self._downloadFinished()
            self.refresh()
        def error_callback(err):
            self.main_window.addToInfoArea(
                unicode(
                    translate(
                        'MainWindow',
                        "Error while downloading new updates: %s"
                        )
                    ) % exceptionAsUnicode(err),
                category=COLOR_CRITICAL
                )
            self.refresh()
        try:
            async = self.client.async()
            async.call(self.component, 'downloadNewUpgrades',
                callback = success_callback,
                errback = error_callback,
            )
            self.main_window.addToInfoArea(
                translate('MainWindow',
                          "Downloading new updates."))
        except RpcdError, err:
            self.main_window.addToInfoArea(
                unicode(translate('MainWindow',
                    "Error while downloading new updates: %s")) %
                    exceptionAsUnicode(err), category=COLOR_CRITICAL)

    def streaming_unsubscribe(self, stream_id):
        streaming = self.client.streaming()
        if streaming is not None and stream_id is not None:
            streaming.unsubscribe(stream_id)

    def downloadProgress(self, counts):
        try:
            if counts.id != self.stream_id:
                self.downloading = 0
                self.streaming_unsubscribe(counts.id)
                self.main_window.addToInfoArea(translate('MainWindow',
                    'The configuration service was restarted while downloading new updates.  Please try again.'), category=COLOR_ERROR)
                self.refresh()
                return
            if counts.data[3]:
                self.main_window.addToInfoArea(translate(
                        'MainWindow', 'Error while downloading new updates: '
                        ) + counts.data[3], category=COLOR_CRITICAL)
                self.streaming_unsubscribe(self.stream_id)
                self.updateDownloadBar(counts.data)
                self.refresh()
                return
            self.updateDownloadBar(counts.data)
            self.refresh()
            if not int(counts.data[2]):
                self._downloadFinished()
        except Exception, err:
            self.streaming_unsubscribe(self.stream_id)
            self.main_window.addToInfoArea(unicode(translate('MainWindow',
                "Error while downloading new updates: %s")) %
                exceptionAsUnicode(err), category=COLOR_CRITICAL)

    def refresh(self):
        try:
            self.uploaded_upgrades = self.main_window.init_call(
                self.component, 'uploadedUpgrades')
        except Exception:  # Resist to Rpcd down:
            if not self.msg_no_connection:
                self.main_window.addToInfoArea(translate('MainWindow',
                    "The server is unreachable."))
                self.msg_no_connection = True
            self.mkTimer()
            return
        try:
            highest_applied = self.main_window.init_call(
                self.component, "getHighestApplied")
            self.highest_applied_label.setText(unicode(highest_applied))
        except Exception:
            pass
        if self.msg_no_connection:
            self.main_window.addToInfoArea(translate('MainWindow',
                "Connection to the server restored."))
            self.msg_no_connection = False
        self.uploadedUpgrades.clearContents()
        self.uploadedUpgrades.setRowCount(len(self.uploaded_upgrades))
        in_progress = False
        pending_need_restart = False
        try:
            for row, upgrade in enumerate(self.uploaded_upgrades):
                if upgrade[4] == UPGRADE_STATUS_IN_PROGRESS:
                    in_progress = True
                if upgrade[4] == UPGRADE_STATUS_NEED_RESTART:
                    pending_need_restart = True
                # Upgrade number:
                self.uploadedUpgrades.setItem(row, 0,
                                              NumberItem('%s' % upgrade[0]))
                # Selected:
                if not upgrade[4] in (UPGRADE_STATUS_IN_PROGRESS,
                                      UPGRADE_STATUS_NEED_RESTART):
                    centeredcheckbox = CenteredCheckBox(self.uploadedUpgrades)
                    checkbox = centeredcheckbox.checkbox
                    self.connect(checkbox, SIGNAL('clicked()'),
                                 partial(self.toggle, upgrade[0], checkbox))
                    checkbox.setChecked(self.selected.get(upgrade[0], 0) != 0)
                    self.uploadedUpgrades.setCellWidget(row, 1,
                                                        centeredcheckbox)
                # Status:
                try:
                    # Avoid (wrong) translation (to be translated in another context).
                    # self.uploadedUpgrades.setItem(row, 2,
                    #     QTableWidgetItem(translate('MainWindow', upgrade[4])))
                    self.uploadedUpgrades.setItem(row, 2,
                        QTableWidgetItem(upgrade[4]))
                except Exception, e:
                    self.main_window.addToInfoArea(unicode(e))
                # Upload date:
                self.uploadedUpgrades.setItem(
                    row, 3, NumberItem('%s' % utc_to_localtime(upgrade[1])))
                # Short changelog:
                self.uploadedUpgrades.setItem(
                    row, 4, QTableWidgetItem('%s' % upgrade[2]))
        except IndexError:
            pass
        self.uploadedUpgrades.horizontalHeader().setResizeMode(
            QHeaderView.ResizeToContents)
        self._detect_end_of_upgrade_application()
        if in_progress:
            if not self._previously_in_progress:
                # Make the progress bar infinite:
                self.progressBar.setMinimum(0)
                self.progressBar.setMaximum(0)
                self.dontStopMeNowLabel.show()
            self.mkTimer()
        else:
            self.dontStopMeNowLabel.hide()
            if self.needRestart:  # Just after the application:
                if self.needRestart == 'ufwi_rpcd':
                    self.main_window.addToInfoArea(translate('MainWindow',
                        'After this or these update(s), you must restart the configuration service.'))
                elif self.needRestart == 'system':
                    self.main_window.addToInfoArea(translate('MainWindow',
                        'After this or these update(s), you must restart the system.'))
                self.question_restart(self.needRestart)
                self.needRestart = ''
                self.mkTimer()
            elif pending_need_restart:
                # Keep refreshing until there is no more restart needed:
                self.mkTimer()
        if in_progress or self.downloading:
            self.progressBar.show()
        else:
            self.progressBar.hide()
        self._previously_in_progress = in_progress

    def restartNucentral(self):
        self.main_window.addToInfoArea(translate('MainWindow',
            'Restarting the configuration service.'))
        try:
            self.client.call('tools', 'restartNucentral')
        except RpcdError:
            self.client.call('tools', 'rebootNucentral')
        self.dialog.close()

    def saveAndCloseServerConf(self):
        self.config.use_custom_mirror = self.tmp_use_custom_mirror
        self.config.update_mirror = unicode(self.update_mirror_edit.text())
        self.config.auto_check = self.tmp_auto_check
        self.setModified(True)
        self.refreshUpdateServerLabel()
        self.dialog.close()

    def toggle(self, upgrade_num, checkbox):
        if checkbox.isChecked():
            self.selected[upgrade_num] = 1
        else:
            try:
                del self.selected[upgrade_num]
            except KeyError:
                pass

    def updateServerCheck(self, state):
        self.tmp_auto_check = bool(state)

    def useCustomMirrorCheck(self, state):
        self.tmp_use_custom_mirror = bool(state)

    # Other functions:

    def mkTimer(self):
        if self.timer is not None and self.timer.isActive():
            self.timer.stop()
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        QObject.connect(self.timer, SIGNAL('timeout()'), self.refresh)
        self.timer.start(REFRESH_INTERVAL_MILLISECONDS)

    def stopTimer(self):
        if self.timer is not None and self.timer.isActive():
            self.timer.stop()

    def createForm(self, page, layout):
        # Toolbar button:
        self.history = QAction(translate('MainWindow', 'History'), self)
        self.history.setToolTip(translate('MainWindow',
                                          'Display updates history'))
        self.contextual_toolbar = ToolBar((self.history,))
        self.contextual_toolbar.setObjectName('Update toolbar')
        self.connect(self.history, SIGNAL('triggered(bool)'),
                     self.display_history)

        highest_applied_group = QGroupBox()
        highest_applied_group.setTitle(
            translate('MainWindow', 'Highest applied update'))
        highest_applied_layout = QHBoxLayout()
        self.highest_applied_text = NuConfPageKit.createLabel(
            translate('MainWindow', 'Highest applied update number:'),
            highest_applied_group)
        self.highest_applied_label = NuConfPageKit.createLabel(
            u'?', highest_applied_group)
        highest_applied_group.setLayout(highest_applied_layout)
        for widget in (self.highest_applied_text, self.highest_applied_label):
            highest_applied_layout.addWidget(widget)
        highest_applied_layout.addStretch()

        update_server_group = QGroupBox()
        update_server_group.setTitle(
            translate('MainWindow', 'Update server'))
        update_server_layout = QHBoxLayout()
        self.update_server_label = NuConfPageKit.createLabel(
            u'', update_server_group)
        self.update_server_edit_button = NuConfPageKit.createButton(
            translate('MainWindow', 'Edit'),
            update_server_group, page, slot=self.displayServerConf,
            icon=QIcon(":/icons/edit"))
        self.update_server_download_button = NuConfPageKit.createButton(
            translate('MainWindow', 'Download new updates'),
            update_server_group, page, self.downloadNewUpgrades,
            icon=QIcon(':/icons/down'))
        update_server_group.setLayout(update_server_layout)
        for widget in (self.update_server_label,
                       self.update_server_edit_button,
                       self.update_server_download_button):
            update_server_layout.addWidget(widget)
        self.main_window.writeAccessNeeded(self.update_server_edit_button,
            self.update_server_download_button)

        self.uploadedUpgrades = QTableWidget(0, 5)
        self.uploadedUpgrades.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.uploadedUpgrades.setSelectionMode(QAbstractItemView.NoSelection)
        self.uploadedUpgrades.horizontalHeader().setStretchLastSection(True)
        self.uploadedUpgrades.verticalHeader().setHidden(True)
        self.uploadedUpgrades.setHorizontalHeaderLabels([
                unicode(translate('MainWindow', 'Number')),
                unicode(translate('MainWindow', 'Selected')),
                unicode(translate('MainWindow', 'Status')),
                unicode(translate('MainWindow', 'Upload date')),
                unicode(translate('MainWindow', 'Changelog'))])

        buttons = QFrame()
        buttons_layout = QGridLayout(buttons)
        sendUpgradeButton = NuConfPageKit.createButton(
            translate('MainWindow', 'Upload update'),
            buttons, page, self.chooseAndSendFile, QIcon(":/icons/up"))
        applyAllButton = NuConfPageKit.createButton(
            translate('MainWindow', 'Apply all'),
            buttons, page, self.applyAll, QIcon(":/icons/status_on"))
        applySelectedButton = NuConfPageKit.createButton(
            translate('MainWindow', 'Apply selected'),
            buttons, page, self.applySelected, QIcon(":/icons/status_on"))
        deleteSelectedButton = NuConfPageKit.createButton(
            translate('MainWindow', 'Delete selected'),
            buttons, page, self.deleteSelected, QIcon(":/icons/delete"))
        refreshButton = NuConfPageKit.createButton(
            translate('MainWindow', 'Refresh'),
            buttons, page, self.refresh, QIcon(':/icons/refresh'))
        self.progressBar = QProgressBar()
        self.progressBar.setFormat('%v')
        # Make this progress bar infinite:
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(0)

        self.main_window.writeAccessNeeded(sendUpgradeButton, applyAllButton,
                applySelectedButton, deleteSelectedButton, refreshButton)
        buttons_layout.addWidget(applyAllButton, 0, 0)
        buttons_layout.addWidget(refreshButton, 0, 1)
        buttons_layout.addWidget(applySelectedButton, 0, 2)
        buttons_layout.addWidget(sendUpgradeButton, 1, 0)
        buttons_layout.addWidget(self.progressBar, 1, 1)
        buttons_layout.addWidget(deleteSelectedButton, 1, 2)

        min_width = 0
        for button in (sendUpgradeButton, applyAllButton, applySelectedButton, deleteSelectedButton, refreshButton, self.progressBar):
            if min_width < button.sizeHint().width():
                min_width = button.sizeHint().width()
        for button in (sendUpgradeButton, applyAllButton, applySelectedButton, deleteSelectedButton, refreshButton, self.progressBar):
            button.setMinimumWidth(min_width)
        # To avoid breaking button alignment:
        self.progressBar.setMaximumWidth(min_width)

        section = NuConfPageKit.addSection(page, layout,
                                 translate('MainWindow', ''),
                                 [highest_applied_group, update_server_group,
                                  self.uploadedUpgrades, buttons])


        section.setFrameShape(QFrame.NoFrame)

        dont_stop_msg = tr('Upgrading. Do not stop the appliance.')
        (dontStopWidget, self.dontStopMeNowLabel) = \
            NuConfPageKit.createLabelInWidget(
            "<span style='color: red; font-weight: bold'>%s</span>" % dont_stop_msg)
        dontStopWidget.layout().setAlignment(Qt.AlignHCenter)
        page.layout().addWidget(dontStopWidget)

        return self

    def refreshUpdateServerLabel(self):
        if self.config.use_custom_mirror:
            self.update_server_label.setText(
                translate('MainWindow', 'Current update server: ') +
                self.config.update_mirror)
        else:
            self.update_server_label.setText(translate('MainWindow',
                'Current update server: EdenWall Technologies server'))

    def saveConf(self, message=''):
        self.config.update_server = unicode(self.update_mirror_edit.text())
        serialized = self.config.serialize()
        self.client.call(self.component, 'setUpdateConfig', serialized,
        message)
        self.main_window.addNeutralMessage(
            translate('MainWindow', 'Update configuration saved.'))
        self.setModified(False)

    def resetConf(self):
        # Objects to store parameters for services to call:
        self.selected = {}

        serialized = self.main_window.init_call(self.component,
                                                u'getUpdateConfig')
        self.config = UpdateCfg.deserialize(serialized)
        self.refreshUpdateServerLabel()
        self.setModified(False)

        self.refresh()

    def updateDownloadBar(self, counts):
        self.progressBar.setValue(int(counts[0]))
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(int(counts[1]))
        self.downloading = int(counts[2])

    def _detect_end_of_upgrade_application(self):
        if self.previous_history is None:
            return
        history = self.client.call(self.component, 'history')
        new_upgrades = history[len(self.previous_history):]
        succeeded_upgrade_nums = []
        failed_upgrade_nums = []
        for upgrade in new_upgrades:
            if upgrade[5]:
                succeeded_upgrade_nums.append(unicode(upgrade[1]))
            else:
                failed_upgrade_nums.append(unicode(upgrade[1]))
        if succeeded_upgrade_nums:
            try:
                self.needRestart = self.client.call(self.component, 'needRestart')
            except Exception:
                self.needRestart = ''
            format = tr(
                'The following upgrade was successfully applied: %s.',
                'The following upgrades were successfully applied: %s.',
                len(succeeded_upgrade_nums))
            message = format % u', '.join(succeeded_upgrade_nums)
            message = htmlBold(htmlColor(message, COLOR_SUCCESS))
            self.main_window.addToInfoArea(message)
        if failed_upgrade_nums:
            self.main_window.addToInfoArea(translate('MainWindow',
                'The following upgrade(s) failed: ') +
                u', '.join(failed_upgrade_nums) + u'.', category=COLOR_CRITICAL)
        self.previous_history = history

    def display_update_locked(self):
        self.main_window.addToInfoArea(translate(
                'Main_Window',
                'Cannot apply the update(s) you have just requested for now (either another update is being applied or new updates are being downloaded).'),
                                       category=COLOR_ERROR)

    def question_restart(self, needRestart):
        hostname = QHostnameObject.getInstance().cfg.hostname
        if needRestart == 'ufwi_rpcd':
            title = translate('MainWindow', 'You need to restart the configuration service on ') \
            + '(%s)' % hostname
        elif needRestart == 'system':
            title = translate('MainWindow', 'You need to restart the system ') \
            + '(%s)' % hostname
        else:
            return
        self.dialog = QDialog(self)
        self.dialog.setModal(False)
        self.dialog.setWindowTitle(title)
        label = NuConfPageKit.createLabel('<h1>%s</h1>' % title, self.dialog)
        layout = QVBoxLayout(self.dialog)
        self.dialog.setLayout(layout)


        # Button box:
        button_box = QDialogButtonBox()
        if needRestart == 'ufwi_rpcd':
            restart_button = QPushButton(translate('MainWindow', 'Restart now'))
            button_box.addButton(restart_button, QDialogButtonBox.AcceptRole)
            cancel_button = QPushButton(translate('MainWindow', 'Cancel'))
            button_box.addButton(cancel_button, QDialogButtonBox.RejectRole)
            self.main_window.connect(button_box, SIGNAL('accepted()'),
                                     self.restartNucentral)
        else:
            close_button = QPushButton(translate('MainWindow', 'Close'))
            button_box.addButton(close_button, QDialogButtonBox.RejectRole)
        self.main_window.connect(button_box, SIGNAL('rejected()'),
                                 self.dialog.close)

        for widget in (label, button_box):
            layout.addWidget(widget)
            widget.show()
        self.dialog.show()

    def deleted_superseded_dialog(self, upgrade_nums):
        if not upgrade_nums:
            return
        dialog = QDialog(self)
        dialog.setModal(False)
        title = translate('MainWindow', 'Deleted superseded updates')
        dialog.setWindowTitle(title)
        label = NuConfPageKit.createLabel('<h1>%s</h1>' % title, dialog)

        if len(upgrade_nums) > 1:
            text = tr('The following superseded updates have been deleted: %s.') \
                % unicode_join(', ', upgrade_nums)
        else:
            text = tr('The superseded update %s has been deleted.') % \
                upgrade_nums[0]
        text_label = QLabel(QString(text))
        layout = QVBoxLayout(dialog)
        dialog.setLayout(layout)
        button = NuConfPageKit.createButton(translate('MainWindow', 'Close'),
                                            dialog, dialog, dialog.close)
        for widget in (label, text_label, button):
            layout.addWidget(widget)
            widget.show()
        dialog.show()

    def unload(self):
        self.stopTimer()
