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


from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QDialog
from PyQt4.QtGui import QDialogButtonBox
from PyQt4.QtGui import QFormLayout
from PyQt4.QtGui import QLineEdit
from PyQt4.QtGui import QTextEdit

from ufwi_rpcd.common import tr
from ufwi_conf.client.qt.message_area import MessageArea

class RestoreConfirmDialog(QDialog):
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)

        box = QFormLayout(self)
        _rest0 = tr("Upload an EdenWall configuration backup. The current "
            "configuration will be lost.")

        _rest1 = tr("You will be able to check the 'System', 'Services' "
            "and 'Firewall' tabs and edit settings to ensure the appliance "
            "post-restoration state still fits your network configuration.")

        items = {
            'title': tr("Description of the restoration process:"),
            'restoration_step0': "%s<br/>%s" % (_rest0, _rest1),
            'restoration_step1': tr("The restoration process will complete when an application is triggered. "
                "To do so, click 'Apply' in the 'Services' or in the 'System' tab; "
                "when the configuration is totally restored, select the relevant "
                "firewall rules in the 'Firewall' tab."),
            'apply_icon':"""<img src=":icons-20/apply"/>""",

        }

        long_text = QTextEdit()
        long_text.setReadOnly(True)
        long_text.setHtml("""
        <span>
        <h2>%(title)s</h2>
        <ol>
        <li>%(restoration_step0)s</li>
        <li>%(restoration_step1)s</li>
        </ol>
        </span>
        """ % items
        )

        box.addRow(long_text)
        msg_area = self._mkMsgArea()
        box.addRow(msg_area)

        title = tr(
            "About to restore the configuration on an EdenWall appliance"
            )
        self.setWindowTitle(title)

        ask_text = "<span>%s</span>" % tr(
            # &#8220; and &#8221; are the xml escapes for english quotation marks
            "Please enter &#8220;yes&#8221;."
            )

        confirm_text = QLineEdit()
        box.addRow(ask_text, confirm_text)

        button_box, self.ok_button, cancel_button = self._mkbuttons()
        box.addRow(button_box)
        self.connect(confirm_text, SIGNAL('textChanged(QString)'), self._enable_ok)

    def _mkbuttons(self):
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
            )

        ok_button = button_box.button(QDialogButtonBox.Ok)
        cancel_button = button_box.button(QDialogButtonBox.Ok)
        ok_button.setEnabled(False)
        ok_button.setText(tr("Continue"))

        self.connect(button_box, SIGNAL('accepted()'), self.accept)
        self.connect(button_box, SIGNAL('rejected()'), self.reject)

        return button_box, ok_button, cancel_button

    def _mkMsgArea(self):
        msg_area = MessageArea()
        warning_title = tr('Last warning')
        warning_message = tr("The restoration process will <b>completely "
            "delete</b> the current configuration of the appliance and "
            "replace it with the configuration supplied in the next step.")
        msg_area.setMessage(warning_title, warning_message, status='warning')
        msg_area.setWidth(65)
        return msg_area

    def _enable_ok(self, qstring):
        value = unicode(qstring)
        self.ok_button.setEnabled(
            value == tr("yes")
        )

