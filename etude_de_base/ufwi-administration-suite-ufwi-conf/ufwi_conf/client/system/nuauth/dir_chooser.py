# -*- coding: utf-8 -*-
# $Id: $

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


from PyQt4.QtCore import SIGNAL, QVariant
from PyQt4.QtGui import (QComboBox, QFrame, QIcon, QScrollArea, QVBoxLayout,
    QWidget)

from ufwi_rpcd.common import tr
from ufwi_conf.client.qt.message_area import MessageArea
from ufwi_conf.common.user_dir import (
    AD,
    KERBEROS,
    KERBEROS_AD,
    LDAP,
    NND,
    NOT_CONFIGURED,
    RADIUS,
    SAME,
    )

from .ad_widget import ADWidget
from .kerberos_widget import KerberosWidget
from .ldap_widget import LdapWidget
from .nnd_widget import NndWidget
from .radius_widget import RadiusUserWidget
from .noconf_widget import NoconfWidget
from .sameasorg import KerberosAdWidget, SameAsOrgAuthWidget

GROUP = 'GROUP'
AUTH = 'AUTH'

LDAP_TEXT = tr('Posix LDAP')
LDAP_ICON = QIcon(':/icons/auth_protocol')
AD_TEXT = tr('Active Directory')
AD_ICON = QIcon(':/icons/windows')
NND_TEXT = tr("Generic LDAP")
NND_ICON = QIcon(':/icons/auth_protocol')
RADIUS_TEXT = tr('Radius')
RADIUS_ICON = QIcon(':/icons/auth_protocol')
KERBEROS_TEXT = tr('Kerberos')
KERBEROS_AD_TEXT = tr('Kerberos / Active Directory')
KERBEROS_ICON = QIcon(':/icons/kerberos')
SAME_TEXT = tr('Authentication provided in the Groups tab')
SAME_ICON = QIcon(':/icons/auth_protocol')
NOT_CONFIGURED_TEXT = tr("No directory")
NOT_CONFIGURED_ICON = QIcon()

USERS_FRONTENDS = {
    RADIUS: (RADIUS_TEXT, RADIUS_ICON, RadiusUserWidget),
    KERBEROS: (KERBEROS_TEXT, KERBEROS_ICON, KerberosWidget),
    SAME: (SAME_TEXT, SAME_ICON, SameAsOrgAuthWidget),
    KERBEROS_AD: (KERBEROS_AD_TEXT, KERBEROS_ICON, KerberosAdWidget),
    NOT_CONFIGURED : (NOT_CONFIGURED_TEXT, NOT_CONFIGURED_ICON, NoconfWidget),
}

GROUPS_FRONTENDS = {
    LDAP: (LDAP_TEXT, LDAP_ICON, LdapWidget),
    AD: (AD_TEXT, AD_ICON, ADWidget),
    NND: (NND_TEXT, NND_ICON, NndWidget),
    NOT_CONFIGURED : (NOT_CONFIGURED_TEXT, NOT_CONFIGURED_ICON, NoconfWidget),
}

def _available_frontends(available_modules, ref):
    return dict(
        (
            (key, ref[key]) for key in available_modules if key != "NOT CONFIGURED"
        )
    )

class VariableConfigFrontend(QFrame):
    def __init__(self, available_modules, config, configs_dict, config_type, mainwindow, parent=None):
        """
        config_type = AUTH|GROUP
        """
        QFrame.__init__(self, parent)
        self.__config_loaded = False
        self.__currentwidget = None

        self.__reserve_parent = QWidget(self)

        self.mainwindow = mainwindow
        if config_type == AUTH:
            frontends = USERS_FRONTENDS
        else:
            frontends = GROUPS_FRONTENDS
        self.choices_dict = _available_frontends(available_modules, frontends)
        self.configs_dict = configs_dict
        self.config_type = config_type
        self.config = config
        self.item_index = {}
        self.__item_widget = {}

        v_box = QVBoxLayout(self)

        self.combo = QComboBox()
        choices_list = list(self.choices_dict.keys())
        choices_list.sort()

        for index, item in enumerate(choices_list):
            text, icon, widget = self.choices_dict[item]
            self.combo.addItem(icon, text, QVariant(item))
            self.item_index[item] = index

        v_box.addWidget(self.combo)

        container_scroll = QScrollArea()
        v_box.addWidget(container_scroll)
        intermediate = QWidget()
        container_scroll.setWidget(intermediate)
        self.container = QVBoxLayout(intermediate)
        container_scroll.setWidgetResizable(True)

        self.message_area = MessageArea()
        v_box.addWidget(self.message_area)

    def __getrelevantconfig(self):
        if self.config_type == AUTH:
            return self.config.auth
        else:
            return self.config.org

    def __setrelevantconfig(self, configpart):
        if self.config_type == AUTH:
            self.config.auth = configpart
        else:
            self.config.org = configpart

    relevantconfig = property(fget=__getrelevantconfig, fset=__setrelevantconfig)

    def __getwidgetclass(self, directory_type):
        if self.config_type == AUTH:
            widget_class = USERS_FRONTENDS[directory_type][-1]
        else:
            widget_class = GROUPS_FRONTENDS[directory_type][-1]
        return widget_class

    def changeWidget(self, index):
        if not self.__config_loaded:
            False
        directory_type = unicode(self.combo.itemData(index).toString())
        self._changeWidget(directory_type)
        self.reemit()

    def _changeWidget(self, directory_type):

        self.__unregisterwidgetsignals()
        widget = self.__getupdatedwidget(directory_type)
        self.__currentwidget = widget
        self.__displaywidget(widget)

        self.__registerwidgetsignals(widget)
        self.__currentwidget.valid(self.message_area)


    def reemit(self, *args):
        self.emit(SIGNAL('modified'), args)
        self.__currentwidget.valid(self.message_area)

    def setViewData(self, config):
        self.config = config
        if self.config_type == AUTH:
            specific = self.config.auth
        else:
            specific = self.config.org
        directory_type = specific.protocol

        if not self.__config_loaded:
            self.connect(self.combo, SIGNAL('currentIndexChanged(int)'), self.changeWidget)
            self.__config_loaded = True

        index = len(self.item_index) - 1
        if directory_type in self.item_index:
            index = self.item_index[directory_type]

        self.combo.setCurrentIndex(index)
        self._changeWidget(directory_type)

    def __getupdatedwidget(self, directory_type):
        cached_config = self.configs_dict[directory_type]

        widget = self.__item_widget.get(directory_type)
        if widget is None:
            widget_class = self.__getwidgetclass(directory_type)
            widget = widget_class(self.config, cached_config, self.mainwindow)
            self.__item_widget[directory_type] = widget
            self.container.addWidget(widget)
        else:
            widget.updateData(self.config, cached_config)
        self.relevantconfig = cached_config
        return widget

    def __displaywidget(self, widget):
        widget.show()

    def __unregisterwidgetsignals(self):
        if self.__currentwidget is None:
            return
        self.__currentwidget.unregister_qobjects()
        self.disconnect(self.__currentwidget, SIGNAL('modified'), self.reemit)
        self.__currentwidget.hide()

    def __registerwidgetsignals(self, widget):
        widget.register_qobjects()
        self.connect(widget, SIGNAL('modified'), self.reemit)

