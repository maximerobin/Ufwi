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

from PyQt4.QtCore import QAbstractTableModel, QModelIndex, Qt, SIGNAL, QVariant
from PyQt4.QtGui import QColor, QIcon, QPixmap

from ufwi_rpcd.common import tr
from ufwi_rpcd.common.tools import abstractmethod
from ufwi_rpcc_qt.genericdelegates import ActionDelegate, BooleanDelegate

from ufwi_conf.common.site2site_cfg import Fingerprint
from ufwi_conf.common.site2site_cfg import VPN, CONNECTED

from .editor import VPNEditor

#VPN COLUMNS
VPN_COLUMNS = (
    VPN_STATUS,
    VPN_IDENTIFIER,
    VPN_ENABLE,
    VPN_GATEWAY,
    VPN_NET_LOCAL,
    VPN_NET_REMOTE,
    VPN_EDIT,
    ) = xrange(7)

_VPN_ENABLE_ROLE = Qt.UserRole + VPN_ENABLE
_VPN_STATUS_ROLE = Qt.UserRole + VPN_STATUS
_VPN_EDIT_ROLE = Qt.UserRole + VPN_EDIT

def _textrole(role):
    return role in (Qt.DisplayRole, Qt.EditRole)

class AbstractSite2SiteModels(QAbstractTableModel):
    def __init__(self, config_container):
        QAbstractTableModel.__init__(self)
        self._config_container = config_container

    def flags(self, index):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

    def rowCount(self, parent=QModelIndex()):
        return self.__dimCount(parent, self._rowCount)

    def columnCount(self, parent=QModelIndex()):
        return self.__dimCount(parent, self._columnCount)

    def insertRow(self, row, parent):
        """
        Only appends
        """
        #actually inserting
        result = self._appenddefault()
        if result:
            #under which row do we insert ?
            #not tested in another setup than appending a row.
            self.beginInsertRows(parent, row, row)
            #we tell views that a row appeared
            self.endInsertRows()
            self.emit(SIGNAL("modified"))
        return result

    def appendvalue(self, value, parent):
        row = self._rowCount()
        result = self._appendvalue(value)
        if result:
            #under which row do we insert ?
            #not tested in another setup than appending a row.
            self.beginInsertRows(parent, row, row)
            #we tell views that a row appeared
            self.endInsertRows()
            self.emit(SIGNAL("modified"))
        return result

    def removeRows(self, row, count, parent):
        last = row + count
        #last - 1 = Last index of the remove rows, we tell the view what rows disappear
        self.beginRemoveRows(parent, row, last - 1)
        #actually remove the rows form the data
        self._removeslice(row, last)
        #we tell views that rows have disappeared
        self.endRemoveRows()
        self.emit(SIGNAL("modified"))
        return True

    @abstractmethod
    def _rowCount(self):
        pass

    @abstractmethod
    def _columnCount(self):
        pass

    @abstractmethod
    def _removeslice(self, begin, end):
        pass

    @abstractmethod
    def _appenddefault(self):
        pass

    def __dimCount(self, parent, method):
        if parent.isValid():
            #Qt doc says, if parent.isValid(), we must return 0 in a table model
            return 0
        count = method()
        self.emit(SIGNAL('candelete'), count > 0)
        return count


class VPNsModel(AbstractSite2SiteModels):

    def __init__(self, rsamodel, config_container):
        AbstractSite2SiteModels.__init__(self, config_container)
        self.__rsamodel = rsamodel

    def update_states(self, states):
        changed = False
        for vpn in self._config_container.config.vpns:
            state = states.get(vpn.identifier)
            if state is not None:
                changed = False
                if state == CONNECTED:
                    vpn.status = True
                else:
                    vpn.status = False
        if changed:
            self.reset()

    def flags(self, index):
        if index.column() == VPN_STATUS:
            return Qt.ItemIsEnabled
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

    def _rowCount(self):
        return len(self._config_container.config.vpns)

    def _columnCount(self):
        return len(VPN_COLUMNS)

    def headerData (self, section, orientation, role):
        """
        section: int
        orientation: Qt.Orientation
        role: default to DisplayRole
        """

        if orientation == Qt.Horizontal:
            if role  != Qt.DisplayRole:
                return QVariant()
            #Display role = header of the column.
            #Decoration role would specify icons, and so on
            if section == VPN_IDENTIFIER:
                name = tr("Identifier")
            elif section == VPN_ENABLE:
                name = tr("Enabled")
            elif section == VPN_STATUS:
                name = tr("Status")
            elif section == VPN_GATEWAY:
                name = tr("Gateway")
            elif section == VPN_NET_LOCAL:
                name = tr("Local network") #Also left network
            elif section == VPN_NET_REMOTE:
                name = tr("Remote network") #Also right network
            else:
                return QVariant()
            return QVariant(name)

        #Qt.Vertical
        if role  != Qt.DisplayRole:
            return QVariant()
        #row number
        return QVariant(unicode(section + 1))

    def __data_vpn_enable(self, vpn, role):
        if role not in (
            Qt.DecorationRole,
            Qt.DisplayRole,
            Qt.BackgroundRole,
            _VPN_ENABLE_ROLE):
            return QVariant()
        return QVariant(vpn.enabled)

        #XXX STUB
        enable = vpn.enabled

        if role == _VPN_ENABLE_ROLE:
            return QVariant(enable)

        if enable:
            if role == Qt.DecorationRole:
                return QVariant(QIcon(":/icons-20/play.png"))
            elif role == Qt.BackgroundRole:
                return QVariant(QColor("#cae1a5"))
            return QVariant(tr("Enabled"))

        if role == Qt.DecorationRole:
            return QVariant(QIcon(":/icons-20/pause.png"))
        elif role == Qt.BackgroundRole:
            return QVariant(QColor("#e6a9ab"))
        return QVariant(tr("Disabled"))

    def __data_vpn_status(self, vpn, role):
        if role not in (
            Qt.DecorationRole,
            Qt.DisplayRole,
            Qt.BackgroundRole,
            _VPN_STATUS_ROLE):
            return QVariant()

        #XXX STUB
        status_on = vpn.status

        if role == _VPN_STATUS_ROLE:
            return QVariant(status_on)

        if status_on:
            if role == Qt.DecorationRole:
                return QVariant(QIcon(":/icons-20/status_on.png"))
            elif role == Qt.BackgroundRole:
                return QVariant(QColor("#cae1a5"))
            return QVariant(tr("On"))

        if role == Qt.DecorationRole:
            return QVariant(QIcon(":/icons-20/status_off.png"))
        elif role == Qt.BackgroundRole:
            return QVariant(QColor("#e6a9ab"))
        return QVariant(tr("Off"))

    def setData(self, index, data, role=Qt.EditRole):
        if not index.isValid():
            return False

        column = index.column()
        vpn = self._config_container.config.vpns[index.row()]

        if role not in (Qt.EditRole, _VPN_EDIT_ROLE, _VPN_ENABLE_ROLE):
            return False

        if column == VPN_IDENTIFIER:
            vpn.identifier = ''.join(unicode(data.toString()).split())
        elif column == VPN_ENABLE:
            vpn.enabled = data.toBool()
        elif column == VPN_GATEWAY:
            vpn.gateway = unicode(data.toString())
        elif column == VPN_NET_LOCAL:
            vpn.local_network = unicode(data.toString())
        elif column == VPN_NET_REMOTE:
            vpn.remote_network = unicode(data.toString())
        elif role != _VPN_EDIT_ROLE:
            #VPN_STATUS, VPN_EDIT
            return False

        row_begin = self.index(index.row(), 0, index)
        row_end = self.index(index.row(), len(VPN_COLUMNS), index)
        self.emit(SIGNAL('dataChanged(QModelIndex,QModelIndex)'), row_begin, row_end)
        return True

    def data(self, index, role):
        """
        index: QModelIndex
        role: Qt.DisplayRole...
        """
        if not index.isValid():
            return QVariant()

        column = index.column()
        vpn = self._config_container.config.vpns[index.row()]

        if role == _VPN_EDIT_ROLE:
            return QVariant(vpn)
        if column == VPN_ENABLE:
            return self.__data_vpn_enable(vpn, role)
        elif column == VPN_STATUS:
            return self.__data_vpn_status(vpn, role)

        if not _textrole(role):
            return QVariant()

        if column == VPN_IDENTIFIER:
            return QVariant(vpn.identifier)
        elif column == VPN_GATEWAY:
            return QVariant(vpn.gateway)
        elif column == VPN_NET_LOCAL:
            return QVariant(vpn.local_network)
        elif column == VPN_NET_REMOTE:
            return QVariant(vpn.remote_network)

#        elif index.column() == VPN_EDIT:
        return QVariant()

    def iterPlaces(self):
        for line in xrange(self._rowCount()):
            for column in xrange(self._columnCount()):
                yield (line, column)

    def iterIndexes(self, restrictcolumn=-1):
        for line, column in self.iterPlaces():
            if restrictcolumn == -1 or restrictcolumn == column:
                yield self.index(line, column)

    def _appenddefault(self):
        new_vpn = VPN()
        editor = VPNEditor(new_vpn, self.__rsamodel)
        result = editor.exec_()
        if result:
            self._config_container.config.vpns.append(new_vpn)
        return result

    def _appendvalue(self, value):
        self._config_container.config.vpns.append(value)
        return True

    def _removeslice(self, begin, end):
        del self._config_container.config.vpns[begin:end]

class VPNEnableDelegate(BooleanDelegate):
    def __init__(self, parent=None):
        pixmap_on = QPixmap(":/icons-20/play.png")
        pixmap_off = QPixmap(":/icons-20/pause.png")
        text_on = tr("enabled")
        text_off = tr("disabled")
        style_on = "background-color: #cae1a5;"
        style_off = "background-color: #e6a9ab;"
        BooleanDelegate.__init__(self, _VPN_ENABLE_ROLE, pixmap_on, pixmap_off,
            text_on, text_off, style_on, style_off, parent)

class VPNEditDelegate(ActionDelegate):
    def __init__(self, rsamodel, parent=None):
        icon = QIcon(":/icons-20/edit.png")
        text = tr("Edit")
        self.__rsamodel = rsamodel
        ActionDelegate.__init__(self, _VPN_EDIT_ROLE, icon, text, self.edititem, parent)

    def edititem(self, index):
        model = index.model()
        item = model.data(index, _VPN_EDIT_ROLE).toPyObject()
        editor = VPNEditor(item, self.__rsamodel)
        if editor.exec_():
            self.setModelData(editor, model, index)

    def setModelData(self, editor, model, index):
        model.setData(index, QVariant(0), self.role)

RSA_COLUMNS = (
    RSA_NAME,
    RSA_PEER,
    RSA_FINGERPRINT
    ) = xrange(3)

class RSAModel(AbstractSite2SiteModels):
    def __init__(self, config_container):
        AbstractSite2SiteModels.__init__(self, config_container)
        #TODO: a fingerprint icon
        self.__key_icon = QIcon()

    def _rowCount(self):
        return len(self._config_container.config.fingerprints)

    def _columnCount(self):
        return len(RSA_COLUMNS)

    def fingerprintAtRow(self, row):
        return self._config_container.config.fingerprints[row]

    def data(self, index, role):
        """
        index: QModelIndex
        role: Qt.DisplayRole...
        """
        if not index.isValid():
            return QVariant()

        fingerprint = self._config_container.config.fingerprints[index.row()]

        column = index.column()
        if column == RSA_NAME:
            if _textrole(role):
                return QVariant(fingerprint.identifier)
            if role == Qt.DecorationRole:
                return QVariant(self.__key_icon)
        if not _textrole(role):
            return QVariant()
            #return QVariant(self.__key_icon) TODO icon should be used for right role
        elif column == RSA_PEER:
            return QVariant(fingerprint.peer)
        elif column == RSA_FINGERPRINT:
            return QVariant(fingerprint.fingerprint)

    def headerData (self, section, orientation, role):
        """
        section: int
        orientation: Qt.Orientation
        role: default to DisplayRole
        """

        if orientation == Qt.Horizontal:
            if role  != Qt.DisplayRole:
                return QVariant()
            #Display role = header of the column.
            #Decoration role would specify icons, and so on
            if section == RSA_NAME:
                name = tr("Identifier")
            elif section == RSA_FINGERPRINT:
                name = tr("Key fingerprint")
            elif section == RSA_PEER:
                name = tr("Associated to peer")
            return QVariant(name)
        #vertical
        if role  != Qt.DisplayRole:
            return QVariant()
        #row number
        return QVariant(unicode(section + 1))

    def setData(self, index, data, role):
        if role != Qt.EditRole:
            return False

        row = index.row()
        column = index.column()

        fingerprint = self._config_container.config.fingerprints[row]

        text = unicode(data.toString())
        if column == RSA_NAME:
            fingerprint.identifier = text
        elif column == RSA_PEER:
            fingerprint.peer = text
        elif column == RSA_FINGERPRINT:
            fingerprint.fingerprint = text
        else:
            return False

        self.emit(SIGNAL('dataChanged(QModelIndex,QModelIndex)'), index, index)
        return True

    def rowOf(self, item):
        for row, fingerprint in enumerate(self._config_container.config.fingerprints):
            if item.unique_id == fingerprint.unique_id:
                return row
        return -1

    def _appenddefault(self):
        self._config_container.config.fingerprints.append(Fingerprint())
        return True

    def _appendvalue(self, value):
        self._config_container.config.fingerprints.append(value)
        return True

    def _removeslice(self, begin, end):
        del self._config_container.config.fingerprints[begin:end]


