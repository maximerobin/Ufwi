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


from logging import debug

from ufwi_rpcd.common.config import serializeElement, deserializeElement, UNSET
from ufwi_rpcd.common.tools import abstractmethod

class DatastructureIncompatible(Exception):
    def __init__(self, msg, server_more_recent=False):
        Exception.__init__(self, msg)
        self.server_more_recent = server_more_recent

class AbstractConf(object):
    """
    Base class for simple configurable items.
    When subclassing, you must redefine ATTRS and ensure __init__ args are in ATTRS order.
    When upgrading a structure version, follow the protocol described further.

    example:

    ATTRS = "directory_type server posix dn_users dn_groups user password".split()
    def __init__(self, directory_type, server, dn_users, dn_groups, user, password, posix=True):
        self._setLocals(locals())


    Upgrade protocol:
    The purpose is that the client returns a downgraded structure to the server,
    so it can still deal with it.
    When subclassing, override checkSerialVersion and downgradeFields.

    * checkSerialVersion must return the received version number and upgrade/create
      the required fields.

    * downgradeFields must tailor the serialized version of the object to fit back the
      previous version. It is normally only used by the client, that will pass the
      keyword argument downgrade=True to serialize.
      DATASTRUCTURE_VERSION is set to the expected value, you don't need to modify it.
      The default implementation does nothing.

    """
    # config module doesn't store inner dict which have only empty values
    # like { 'key1':{} }
    # if AbstractConf attributes which are dict or list don't contains
    # dict or list, this hack works

    ATTRS=()

    DATASTRUCTURE_VERSION = -1

    def __init__(self):
        #default, can be erased
        self._received_version = self.DATASTRUCTURE_VERSION

    def copy(self):
        """ Get a copy of an abstract conf. This is useful when editing an
        abstract conf in a dialog box, to be able to discard without changing
        the original abstract conf if the admin cancels the dialog box.
        Caution: It is not guaranted to work for every abstract conf."""
        serialized = self.serialize()
        return self.__class__.deserialize(serialized)

    def serialize(self, downgrade=False):
        result = {}
        for attr in self.__class__.ATTRS:
            val = getattr(self, attr)
            result[attr] = self.serializeElement(val)
        result['DATASTRUCTURE_VERSION'] = self.DATASTRUCTURE_VERSION
        result['__type__'] = '%s.%s' % (self.__module__, type(self).__name__)

        if downgrade:
            self._downgrade(result)
        return result

    def _downgrade(self, result):
        wanted_version = self.getReceivedSerialVersion()
        if result['DATASTRUCTURE_VERSION'] == wanted_version:
            return
        self.downgradeFields(result, wanted_version)
        result['DATASTRUCTURE_VERSION'] = wanted_version

    def downgradeFields(self, serialized, wanted_version):
        """
        You want to override this default implementation
        """
        return serialized

    def _setLocals(self, locals):
        for key, value in locals.iteritems():
            if key != "self":
                setattr(self, key, value)

    @classmethod
    def _deserialize(cls, serialized):
        received_version = cls.checkSerialVersion(serialized)

        rewritten = dict(serialized)
        for attr, val in serialized.iteritems():
            if val == UNSET:
                rewritten[attr] = None
        params = {}
        for attr in cls.ATTRS:
            val = rewritten[attr]
            params[attr] = cls.deserializeElement(val)
        result = cls(**params)
        result.setReceivedSerialVersion(received_version)
        return result

    def setReceivedSerialVersion(self, version):
        self._received_version = version

    def getReceivedSerialVersion(self):
        """
        The version of the serialized structure we got
        """
        return self._received_version

    def iter_attr_and_values(self):
        for attr in self.ATTRS:
            yield attr, getattr(self, attr)

    def iter_attr_and_textvalues(self):
        for attr, value in self.iter_attr_and_values():
            yield attr, unicode(value)

    @classmethod
    def checkSerialVersion(cls, serialized):
        """
        returns the datastructure version
        """
        if -1 == cls.DATASTRUCTURE_VERSION:
            raise NotImplementedError("'%s' have no 'DATASTRUCTURE_VERSION'" % cls)
        datastructure_version = serialized.get('DATASTRUCTURE_VERSION')
        if datastructure_version != cls.DATASTRUCTURE_VERSION:
            cls.raise_version_error(datastructure_version)
        return datastructure_version

    @classmethod
    def serializeElement(cls, value):
        return serializeElement(value, extensions=((AbstractConf, 'serialize'),))

    @classmethod
    def deserializeElement(cls, serialized):
        try:
            return deserializeElement(serialized)
        except:
            debug("problem deserializing %s" % serialized)
            raise

    @classmethod
    def deserialize(cls, serialized):
        return cls._deserialize(serialized)

    def isValid(self):
        ok, msg = self.isValidWithMsg()
        return ok

    @abstractmethod
    def isValidWithMsg(self):
        pass

    @classmethod
    def raise_version_error(cls, datastructure_version):
        raise DatastructureIncompatible(
            'received incompatible %s object, expected %r, got %r' % (
                cls.__name__, cls.DATASTRUCTURE_VERSION, datastructure_version),
                server_more_recent=cls.DATASTRUCTURE_VERSION < datastructure_version)

