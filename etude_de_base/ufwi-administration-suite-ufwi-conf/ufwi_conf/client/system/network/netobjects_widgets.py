#coding: utf-8

from PyQt4.QtCore import Qt, SIGNAL

from PyQt4.QtGui import (QCheckBox, QColor, QComboBox, QFormLayout, QFrame,
    QHBoxLayout, QIcon, QLabel, QLineEdit, QPalette, QRegExpValidator,
    QSpinBox, QVBoxLayout, QWidget)

from ufwi_rpcd.client import tr
from ufwi_rpcc_qt.central_dialog import IPV4_REGEXP, IPV6_REGEXP
from ufwi_rpcc_qt.input_widgets import Button
from ufwi_conf.client.qt.input_widgets import EditButton

class ColoredThing(object):
    """
    To be used in conjunction with another class...
    """
    def setColors(self, bg_color, fg_color):
        self.setAutoFillBackground( True )
        palette = self.palette()
        palette.setColor( QPalette.Window, QColor(bg_color) )
        palette.setColor( QPalette.WindowText, QColor(fg_color) )

class ObjectDetails(QWidget, ColoredThing):
    def __init__(self, data, button, parent=None):
        QWidget.__init__(self, parent)
        self.button = button
        self.form = QFormLayout(self)
        for item in data:
            self.form.addRow(item[0], item[1])
        self.connect(button, SIGNAL('clicked()'), self.updateView)
        self.updateView()

    def updateView(self):
        self.setVisible(self.button.expanded)

class NetObjectMain(ColoredThing, QFrame):
    def __init__(self, net_object, title, details_widget, parent=None, debug=False):
        QFrame.__init__(self, parent)
        ColoredThing.__init__(self)
        self.title = title
        self.net_object = net_object
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.box_layout = QVBoxLayout(self)
        self.box_layout.setMargin(0)
        self.box_layout.setAlignment(Qt.AlignTop)
        self.box_layout.addWidget(title)
        self.object_details = details_widget
        self.box_layout.addWidget(self.object_details)

class InterfaceChoice(QComboBox):
    def __init__(self, ifaces, parent=None):
        QComboBox.__init__(self, parent)
        self.setEditable(False)
        self.setToolTip("Select a network interface")

        self.labels2ifaces = {}
        for iface in ifaces:
            self.labels2ifaces[iface.user_label] = iface

        self.addItems(self.labels2ifaces.keys())

    def getSelection(self):
        label = unicode(self.currentText())
        return label, self.labels2ifaces[label]

class IPVersionInput(QComboBox):
    def __init__(self, parent=None):
        QComboBox.__init__(self, parent)
        self.addItems(["ipv4", "ipv6"])
        self.setToolTip("Choose IP version")

        self.ip_version = 4

        self.connect(self, SIGNAL('currentIndexChanged(QString)'), self.change)

    def change(self, version):
        self.ip_version = 4 if version == "ipv4" else 6
        self.emit(SIGNAL('ip_version_changed'), self.ip_version)

class AddressAndMaskInput(QWidget):
    def __init__(self, ip_version=4, parent=None):
        QWidget.__init__(self, parent)

        self.address = QLineEdit()
        self.prefix = QSpinBox()
        self.prefix.setMinimum(0)

        self.setVersion(ip_version)
        layout = QHBoxLayout(self)

        layout.addWidget(self.address)
        layout.addWidget(QLabel("<h2>/</h2>"))
        layout.addWidget(self.prefix)

    def setVersion(self, ip_version):
        if ip_version == 4:
            self.ip_regex = IPV4_REGEXP
            mask_size = 31
        else:
            self.ip_regex = IPV6_REGEXP
            mask_size = 127

        validator = QRegExpValidator(self.ip_regex, self.address)
        self.address.setValidator(validator)
        self.prefix.setMaximum(mask_size)

    def showValid(self, valid):
        if valid:
            style = u''
        else:
            style = u'background: #b52323;'

        for widget in (self.prefix, self.address):
            widget.setStyleSheet(style)

class NetObjectTitle(QWidget):
    def __init__(self, text_items, abstract, menu, parent=None):
        QWidget.__init__(self, parent)
        self.row_layout = QHBoxLayout(self)
        self.row_layout.setMargin(0)
        self.row_layout.setAlignment(Qt.AlignLeft)
        self.details_button = DetailsButton()
        self.row_layout.addWidget(self.details_button)

        for widget in (self.details_button, self):
            self.connect(widget, SIGNAL('clicked()'), self.updateView)

        for text in text_items:
            label = QLabel()
            label.setText("<h2>%s</h2>" % text)
            self.row_layout.addWidget(label)

        self.abstract = abstract

        if abstract is None:
            return

        self.row_layout.addWidget(abstract)
        self.row_layout.addStretch()

        self.edit_button = EditButton(menu)
        self.row_layout.addWidget(self.edit_button)

    def updateView(self):
        if self.abstract is None:
            return

        if self.details_button.expanded:
            self.abstract.hide()
        else:
            self.abstract.show()

    def mouseDoubleClickEvent(self, event):
        """
        double clicking on elements' title bar has the same effect
        as clicking on expand/collapse button
        """
        self.details_button.emit(SIGNAL('clicked()'))

class DetailsButton(Button):
    _ICONS = None
    _TOOLTIPS = None

    @staticmethod
    def _mkStatics():
        DetailsButton._ICONS = {
            True: QIcon(":/icons/fold"),
            False: QIcon(":/icons/unfold")
        }
        DetailsButton._TOOLTIPS = {
            True: tr("Click to fold"),
            False: tr("Click to unfold")
        }

    def __init__(self, parent=None):
        Button.__init__(self, parent)
        if DetailsButton._ICONS is None:
            DetailsButton._mkStatics()
        self.expanded = False
        self.connect(self, SIGNAL('clicked()'), self.clicked)
        self.updateView()


    def clicked(self):
        self.toggle()
        self.updateView()

    def toggle(self):
        self.expanded = not self.expanded

    def updateView(self):
        self.setIcon(DetailsButton._ICONS[self.expanded])
        self.setToolTip(DetailsButton._TOOLTIPS[self.expanded])

class HidingWidget(QWidget):
    def __init__(self, button, parent=None):
        QWidget.__init__(self, parent)
        self.button = button
        self.updateView()
        self.connect(button, SIGNAL('clicked()'), self.updateView)

    def updateView(self):
        self.setVisible(self.button.expanded)

class QuickFormLayout(QFormLayout):
    def _add(self, question, widget):
        self.addRow(question, widget)
        return widget

    def addBoolean(self, question, default=False):
        w = QCheckBox()
        w.setChecked(default)
        return self._add(question, w)

    def addString(self, question, default=""):
        w = QLineEdit()
        w.setText(default)
        return self._add(question, w)

