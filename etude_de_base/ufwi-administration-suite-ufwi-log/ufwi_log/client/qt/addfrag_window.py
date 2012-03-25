# -*- coding: utf-8 -*-

"""
Copyright (C) 2008-2011 EdenWall Technologies
Written by Romain Bignon <romain AT inl.fr>

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

$Id$
"""

from PyQt4.QtGui import QDialog, QDialogButtonBox, QWidget, QCheckBox
from PyQt4.QtGui import QMessageBox, QColorDialog, QColor
from PyQt4.QtCore import QVariant, SIGNAL
from ui.addfrag_ui import Ui_AddFragDialog
from copy import deepcopy

#from ufwi_log.client.qt.views import views_list
#from ufwi_log.client.qt.fragtypes import frag_types
#from ufwi_log.client.qt.args import arg_types, CheckError

#from views import views_list
from ufwi_rpcd.common import tr
from views.graphics_view import GraphicsView
from fragtypes import frag_types
from args import arg_types
from args.argfilter import CheckError

class AddFragDialog(QDialog):
    def __init__(self, window, fragment=None, parent=None):
        """
            @param window [NulogMainWindow] the window where we edit fragment
            @param fragment [Fragment] the edited fragment
        """

        QDialog.__init__(self, parent)
        self.ui = Ui_AddFragDialog()
        self.ui.setupUi(self)

        self.window = window
        self.compatibility = window.user_settings.compatibility
        self.fragment = fragment
        self.is_new = not fragment
        self.args = []
        self.background_color = None
        self.last_firewall = None

        self.connectSignals()

    def connectSignals(self):
        self.connect(self.ui.type, SIGNAL('currentIndexChanged(int)'), self.typeChanged)
        self.connect(self.ui.color_button, SIGNAL('clicked(bool)'), self.colorChanged)

    def colorChanged(self, ok):
        color = QColorDialog.getColor(QColor(self.fragment.background_color))

        # user cancelled
        if not color.isValid():
            return

        # remove the alpha channel
        self.background_color = color.rgb() & 0x00ffffff
        self.ui.color.setStyleSheet('background-color: rgb(%d, %d, %d)' % (color.red(), color.green(), color.blue()))

    def typeChanged(self, index):
        """
            Type is changed, index is the new selected index
        """

        self.ui.view.clear()

        # If nothing is selected
        if index < 0:
            self.ui.title_label.setEnabled(False)
            self.ui.title.setEnabled(False)
            self.ui.title.setText('')
            self.ui.view_label.hide()
            self.ui.view.hide()
            self.ui.color_label.setEnabled(False)
            self.ui.color_button.setEnabled(False)
            self.ui.firewall.setEnabled(False)
            self.ui.firewall_label.setEnabled(False)
            self.ui.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)
            self._set_args(False)
            return

        fragtypename = unicode(self.ui.type.itemData(index).toString())
        fragtype = frag_types[fragtypename]
        if not self.fragment or self.fragment.type != fragtypename:
#            self.window.user_settings.removeFragment(self.fragment)
            self.fragment = self.window.user_settings.createFragment(fragtypename, False)

        self.ui.title_label.setEnabled(True)
        self.ui.title.setEnabled(True)
        self.ui.title.setText(fragtype.title)
        self.ui.view_label.setEnabled(True)
        self.ui.view.setEnabled(True)
        self.ui.color_label.setEnabled(True)
        self.ui.color_button.setEnabled(True)
        self.ui.firewall.setEnabled(True)
        self.ui.firewall_label.setEnabled(True)

        # Add views related to this fragment type.
        for view in fragtype.views:
#            if not views_list.has_key(view):
#                continue
            if not isinstance(view, GraphicsView):
                continue
#            self.ui.view.addItem(views_list[view].name(), QVariant(view))
            self.ui.view.addItem(view.name(), QVariant(view))

        if len(fragtype.views) > 1:
            self.ui.view_label.show()
            self.ui.view.show()
        else:
            self.ui.view_label.hide()
            self.ui.view.hide()

        # Set the fragment background color
        color = QColor(self.fragment.background_color)
        self.ui.color.setStyleSheet('background-color: rgb(%d, %d, %d)' % (color.red(), color.green(), color.blue()))

        # Firewall
        i = self.ui.firewall.findData(QVariant(self.fragment.firewall))
        self.ui.firewall.setCurrentIndex(i)

        self._set_args()

        self.ui.buttonBox.button(QDialogButtonBox.Ok).setEnabled(True)

    def firewallChanged(self, i):
        if i < 0:
            return

        self.fragment.firewall = unicode(self.ui.firewall.itemData(i).toString())
        self._set_args()

    def _set_args(self, fetch=True):
        for arg_checkbox, arg_value in self.args:
            if arg_checkbox:
                self.ui.args.layout().removeWidget(arg_checkbox)
                arg_checkbox.hide()
            if arg_value:
                self.ui.args.layout().removeWidget(arg_value)
                arg_value.hide()
        self.args = []

        if not fetch:
            self.ui.args.setEnabled(False)
            return

        # Show arguments availables for this fragment type.
        try:
            args = frag_types[self.fragment.type].fetcher(self.fragment, {}, self.window.client).getArgs()
        except:
            args = {}

        if not args:
            self.ui.args.setEnabled(False)
            return

        self.ui.args.setEnabled(True)
        for arg in args:

            value = ''
            # There is already a value for this argument.
            if self.fragment.args.has_key(arg):
                value = self.fragment.args[arg]

            # Get the widget which will be used
            try:
                arg_value = arg_types[arg].filter(self.window.client, arg, value, compatibility=self.compatibility)
            except KeyError:
                continue
            if not isinstance(arg_value, QWidget):
                continue

            # Add a checkbox to activate or no this argument.
            arg_checkbox = QCheckBox(arg_types[arg].label)
            if not (value is None or value == ''):
                arg_checkbox.setChecked(True)
                arg_value.setEnabled(True)
            else:
                arg_checkbox.setChecked(False)
                arg_value.setEnabled(False)
            self.connect(arg_checkbox, SIGNAL('toggled(bool)'), arg_value.setEnabled)

            self.ui.args.layout().addWidget(arg_checkbox, len(self.args), 0)
            self.ui.args.layout().addWidget(arg_value, len(self.args), 1)

            self.args += [(arg_checkbox, arg_value)]

    def run(self):
        """
            Run the dialog box and add a fragment to it if fragment=None.
            In other case, we edit it.

        """
        if self.window.client.call('CORE', 'hasComponent', 'multisite_master'):
            firewalls = self.window.client.call('multisite_master', 'listFirewalls')
            self.ui.firewall.addItem(self.tr('EMF appliance'), QVariant(''))
            for fw, state, error, last_seen, ip in firewalls:
                self.ui.firewall.addItem(unicode(self.tr('Host firewall: %s')) % fw, QVariant(fw))
            self.connect(self.ui.firewall, SIGNAL('currentIndexChanged(int)'), self.firewallChanged)
        else:
            self.ui.firewall.hide()
            self.ui.firewall_label.hide()

        if not self.is_new:
            self.ui.type.addItem('%s - %s' % (self.fragment.type, self.tr(frag_types[self.fragment.type].title.encode("UTF-8"))), QVariant(self.fragment.type))
            self.ui.type.setEnabled(False)
            self.ui.type_label.setEnabled(False)

            self.ui.title.setText(self.fragment.title)

            index = self.ui.view.findData(QVariant(self.fragment.view))
            self.ui.view.setCurrentIndex(index)

            index = self.ui.firewall.findData(QVariant(self.fragment.firewall))
            self.ui.firewall.setCurrentIndex(index)
            self.last_firewall = self.fragment.firewall

            self.setWindowTitle(self.tr('Edit a fragment'))
        else:
            types = frag_types.items()
            types.sort()
            for label, frag in types:
                self.ui.type.addItem('%s - %s' % (label, tr(str(frag.title))), QVariant(label))

            self.ui.type.setCurrentIndex(-1)

        while 1:
            if not self.exec_() or not self.fragment:
                if self.fragment:
                    if not self.last_firewall is None:
                        self.fragment.firewall = self.last_firewall
                    if self.is_new:
                        self.window.user_settings.removeFragment(self.fragment)
                return False

            try:
                # Fetch arguments values before edit the 'self.fragment' object,
                # because the arg_filter.getValue() method can raises an
                # exception, and in this case we tell user that there is an
                # unvalid value in any field.
                args = deepcopy(self.fragment.args)
                for arg_checkbox, arg_filter in self.args:
                    if arg_checkbox.isChecked():
                        args[arg_filter.filter_arg] = arg_filter.getValue()
                    else:
                        try:
                            args.pop(arg_filter.filter_arg)
                        except KeyError:
                            pass

                self.fragment.title = unicode(self.ui.title.text())
                self.fragment.view = unicode(self.ui.view.itemData(self.ui.view.currentIndex()).toString())
                self.fragment.args = deepcopy(args)
                if not self.background_color is None:
                    self.fragment.background_color = self.background_color

                if self.is_new:
                    self.window.addFragment(self.fragment)
                    self.window.current_page.addFragment(self.fragment)
                    self.window.addFragRemoveAction(self.fragment.title, self.fragment.name)
                else:
                    self.fragment.setDefault(False)

                return True

            except CheckError, e:
                QMessageBox.critical(self, self.tr("Invalid argument"),
                                           unicode(e), QMessageBox.Ok)

