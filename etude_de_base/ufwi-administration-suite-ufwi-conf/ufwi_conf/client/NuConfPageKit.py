# Common functions for specific form creation methods.
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


from PyQt4.QtGui import (QApplication, QButtonGroup, QCheckBox,
    QComboBox, QLineEdit, QFont, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QPushButton, QSizePolicy, QTableWidget, QTableWidgetItem, QTextBrowser,
    QVBoxLayout, QWidget)
from PyQt4.QtCore import QCoreApplication, QString, QStringList, Qt, SIGNAL
translate = QCoreApplication.translate

pageFontSize = 14
sectionFontSize = 12

# Sizes of columns for lists:
deleteButtonColumnWidth = 70
totalWidth = 350
contentColumnWidth = totalWidth - deleteButtonColumnWidth

BUTTON_IDX = 1
INPUT_IDX = 0

assert INPUT_IDX != BUTTON_IDX

def warning(s):
    print '***** Warning: %s' % s

def createButton(text, widget, main_window=None, slot=None, icon=None):
    if icon:
        b = QPushButton(icon, text, widget)
    else:
        b = QPushButton(text, widget)
    b.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    if main_window and slot:
        main_window.connect(b, SIGNAL('clicked()'), slot)
    return b

def createFrame(parent, name=None):
    frame = QFrame(parent)
    frame.setFrameShape(QFrame.StyledPanel)
    frame.setFrameShadow(QFrame.Raised)
    if name:
        frame.setObjectName(name)
    return frame

def createLabel(text, parent=None):
    label = QLabel(text, parent)
    label.setMargin(1)
    return label

def createLineEdit(parent, changedSlot, validator=None):
    lineedit = QLineEdit(parent)
    if changedSlot:
        parent.connect(lineedit, SIGNAL('textChanged(const QString&)'),
                changedSlot)
    if validator:
        lineedit.setValidator(validator(parent))
    return lineedit

def _createTitleLabel(text, size=sectionFontSize):
    label = QLabel(text)
    font = QFont(label.font())
    font.setPointSize(size)
    font.setWeight(75)
    font.setBold(True)
    label.setFont(font)
    label.setWordWrap(True)
    return label

def createSectionLabel(text):
    return _createTitleLabel(text)

def createPageLabel(text):
    title = '<H1>%s</H1>' % text
    return QLabel(title)

def createLink(text, parent, main_window, slot):
    link = createLabel('<a href="#">' + text + '</a>', parent)
    link.setCursor(Qt.PointingHandCursor)
    link.setTextInteractionFlags(Qt.TextSelectableByMouse |
            Qt.LinksAccessibleByMouse | Qt.LinksAccessibleByKeyboard)
    main_window.connect(link, SIGNAL('linkActivated(const QString&)'), slot)
    return link


def createHorizontalWidget():
    widget = QWidget()
    sub_layout = QHBoxLayout()
    widget.setLayout(sub_layout)
    return widget

def createInertTableItem(text):
    item = QTableWidgetItem(text)
    item.setFlags(Qt.ItemIsEnabled)
    return item

def _createLabelInWidget(labelText, layoutType):
    widget = QWidget()
    sub_layout = layoutType()
    sub_layout.setObjectName('labelInWidgetSubLayout')
    widget.setLayout(sub_layout)
    label = createLabel(labelText)
    if isinstance(sub_layout, QGridLayout):
        sub_layout.addWidget(label, 0, 0)
    else:
        sub_layout.addWidget(label)
    return (widget, label)

def createLabelInWidget(labelText):
    return _createLabelInWidget(labelText, QHBoxLayout)

def createLabelAndButton(labelText, buttonText, main_window=None, slot=None):
    (widget, label) = createLabelInWidget(labelText)
    button = createButton(buttonText, widget, main_window, slot)
    widget.layout().addWidget(button)
    return (widget, label, button)

def createLabelAndCheckBox(labelText, changedSlot):
    # is it really needed to have 2 widgets ?
    widget = QWidget()

    sub_layout = QHBoxLayout()
    sub_layout.setObjectName('labelAndCheckBoxLayout')

    widget.setLayout(sub_layout)

    checkBox = QCheckBox(widget)
    widget.connect(checkBox, SIGNAL('stateChanged(int)'), changedSlot)
    checkBox.setText(labelText)
    checkBox.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)

    sub_layout.addWidget(checkBox)
    sub_layout.addStretch(100)

    return (widget, checkBox)

def createLabelAndCombobox(labelText):
    (widget, label) = createLabelInWidget(labelText)
    combobox = QComboBox(widget)
    widget.layout().addWidget(combobox)
    return (widget, label, combobox)

def createLabelAndLineEdit(labelText, changedSlot, validator=None):
    (widget, label) = createLabelInWidget(labelText)
    lineedit = createLineEdit(widget, changedSlot, validator)
    widget.layout().addWidget(lineedit)
    return (widget, label, lineedit)

def createLabelAndList(labelText):
    widget, label = _createLabelInWidget(labelText, QGridLayout)
    buttonGroup = QButtonGroup(widget)
    buttonGroup.setObjectName('buttonGroup')
    buttonGroup.setExclusive(False)
    return (widget, label, buttonGroup)

def createQStringList(stringList):
    stringList = QStringList()
    for s in stringList:
        stringList.append(QString(s))
    return stringList

def createList(labelText, slot, changedSlot, validator=None):
    widget = QWidget()
    layout = QVBoxLayout()
    layout.setObjectName('listLayout')
    widget.setLayout(layout)
    hboxWidget = QWidget()
    hboxLayout = QHBoxLayout()
    hboxLayout.setObjectName('hboxLayout for tableWidget')
    hboxWidget.setLayout(hboxLayout)
    tableWidget = QTableWidget(0, 2)
    tableWidget.setAlternatingRowColors(True)
    widget.connect(tableWidget, SIGNAL('cellChanged(int, int)'), changedSlot)
    tableWidget.setHorizontalHeaderLabels(createQStringList([labelText, '']))
    tableWidget.setColumnWidth(INPUT_IDX, contentColumnWidth)
    tableWidget.setColumnWidth(BUTTON_IDX, deleteButtonColumnWidth)
    hboxLayout.addWidget(tableWidget)

    add = QWidget()
    addLayout = QHBoxLayout()
    addLayout.setObjectName('addLayout')
    add.setLayout(addLayout)
    addLineEdit = createLineEdit(add, None, validator)
    addButton = createButton(translate('MainWindow', 'Add'), add, add,
            slot)
    add.connect(addLineEdit, SIGNAL('returnPressed()'), slot)
    for wid in addLineEdit, addButton:
        addLayout.addWidget(wid)

    for wid in add, hboxWidget:
        layout.addWidget(wid)
    return (widget, tableWidget, addLineEdit)

def createText(parent, name=None):
    text = QTextBrowser(parent)
    text.setReadOnly(True)
    if name:
        text.setObjectName(name)
    return text

def addSection(form, layout, title, widgets):

    sub_frame = QFrame(form)
    sub_frame.setObjectName('sectionFrame')
    sub_frame.setFrameShape(QFrame.StyledPanel)
    sub_frame.setFrameShadow(QFrame.Raised)
    sub_frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)

    sub_layout = QVBoxLayout(sub_frame)
    sub_layout.setObjectName('sectionLayout')
    sub_layout.setMargin(4)
    sub_layout.setSpacing(2)

    if title:
        sub_layout.addWidget(createSectionLabel(title))

    for widget in widgets:
        if widget:
            sub_layout.addWidget(widget)
        else:
            warning('Null widget for section "%s".' % unicode(title))
    sub_frame.setLayout(sub_layout)
    layout.addWidget(sub_frame)
    return sub_frame

def disableModuleForm(layout):
    layout.addWidget(createLabel(QApplication.translate('MainWindow',
        'This module is disabled.')))

def checkRadioButton(buttons, value, default=None):
    for button in buttons.values():
        button.setChecked(False)
    try:
        buttons[value].setChecked(True)
        return True
    except KeyError:
        try:
            buttons[default].setChecked(True)
            return True
        except KeyError:
            return False

def getCheckedRadioButton(buttons):
    for key, button in buttons.items():
        if button.isChecked():
            return key
    return None
