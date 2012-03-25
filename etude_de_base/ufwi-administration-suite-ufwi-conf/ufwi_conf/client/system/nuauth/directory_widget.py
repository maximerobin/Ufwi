
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

from ufwi_rpcd.common.tools import abstractmethod

from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QFrame
from PyQt4.QtGui import QFormLayout
from PyQt4.QtGui import QLineEdit

from ufwi_rpcd.common import tr

class DirectoryWidget(QFrame):
    def __init__(self, config, specific_config, mainwindow, parent=None):
        """
        function can be either auth or group
        """

        QFrame.__init__(self, parent)
        self.texts = set()
        self.mainwindow = mainwindow
        self.config = None
        self.specific_config = None
        self.updateData(config, specific_config, updateview=False)
        self.form = QFormLayout(self)

    def readString(self, qstring):
        return unicode(qstring).strip()

    def signalModified(self):
        self.emit(SIGNAL('modified'))

    def addTextInput(self, question, callback, visible=True):
        text_input = QLineEdit()
        self.form.addRow(question, text_input)

        def texthandler():
            text = unicode(text_input.text())
            if visible:
                #don't alter what you can't see
                text = text.strip()
            text_input.setText(text)
            callback(text)
            if unicode(text) != text_input.default_value or len(text_input.default_value) == 0:
                self.signalModified()

        def setDefaultText(value):
            text_input.default_value = value
            text_input.setText(value)

        def maybemodified(qstring):
            if unicode(qstring) != text_input.default_value:
                self.signalModified()

        text_input.setDefaultText = setDefaultText
        text_input.default_value = ''

        self.connect(text_input, SIGNAL('editingFinished()'), texthandler)
#        self.connect(text_input, SIGNAL('textChanged(QString)'), maybemodified)

        if not visible:
            text_input.setEchoMode(QLineEdit.Password)
        return text_input

    def setDefaultText(self, line_edit, value):
        if value is not None:
            line_edit.setDefaultText(value)

    def setText(self, line_edit, value):
        if value is not None:
            line_edit.setText(value)

    def _safeText(self, text):
        if text is None:
            return u''
        return text

    def syncTexts(self):
        """
        same as above
        """
        pass

    def isFilled(self):
        for item in self.texts:
            if not item.text().isEmpty():
                return True
        return False

    def register_qobjects(self):
        """
        Default implementation does nothing
        """
        pass

    def unregister_qobjects(self):
        """
        Default implementation does nothing
        """

    def updateData(self, config, specific_config, updateview=True):
        assert config is not None
        assert specific_config is not None
        self.config = config
        self.specific_config = specific_config
        if updateview:
            self.updateView()

    @abstractmethod
    def updateView(self):
        pass

    def valid(self, message_area):
        ok, msg = self.config.isValidWithMsg()
        title = tr("Configuration validation")
        if ok:
            message_area.info(
                title,
                tr("Valid Directory configuration.")
                )
            return
        message_area.warning(
            title,
            msg
            )




