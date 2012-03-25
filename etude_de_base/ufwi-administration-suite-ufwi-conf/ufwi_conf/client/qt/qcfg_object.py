
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

from PyQt4.QtCore import QObject, Qt
from PyQt4.QtCore import SIGNAL

from ufwi_rpcd.common.logger import Logger
from ufwi_conf.common.id_store import PersistentID

NOARG = object()

class QConfigObject(QObject):
    """
    Singleton object.
    Holds a *cfg, and notices you with a 'modified' SIGNAL

    The reason of this object is that it is difficult to find a frontend module,
    listen for its modifications and react accordingly.
    The singleton reflects the user seing a unique data set, and this can be refactored
    later of we need several ufwi_conf interfaces talking to several edenwalls.

    """

    _instance = None

    def __init__(self, deserialize_fn, cfg_name, set_fn_name, parent=None):
        QObject.__init__(self, parent)
        #name of a model -> model
        self.models = {}
        if isinstance(parent, Logger):
            self.logger = parent
        else:
            self.logger = Logger(cfg_name)

        self.cfg = None
        self.validation_callbacks = []
        self.passed_args = []
        self.effective_callbacks = []
        self.__forgettables = {}

        self.backup = None

        cls = self.__class__
        setattr(
            cls,
            cfg_name,
            property(fget=cls.getCfg, fset=cls.setCfg)
            )

        setattr(
            self,
            set_fn_name,
            self.setCfg
            )

        setattr(
            self.__class__,
            'deserialize',
            staticmethod(deserialize_fn)
            )

    def resetModels(self):
        """
        A method that should be subclassed
        """
        pass

    def hasConfig(self):
        """
        return if object have a config
        """
        return self.cfg != None

    @classmethod
    def getInstance(cls):
        if cls._instance is None:
            cls._instance = cls()

        return cls._instance

    def registerCallbacks(self, canHandleModification, handleModification, attach=None):
        self.validation_callbacks.append(canHandleModification)
        self.effective_callbacks.append(handleModification)

        if attach is not None:
            self.connect(attach, SIGNAL('destroyed(QObject)'), self.forget)
            self.__forgettables[attach] = canHandleModification, handleModification

    def forget(self, qobject):
        callbacks = self.__forgettables.get(qobject)
        if callbacks is None:
            return
        canHandleModification, handleModification = callbacks
        del self.__forgettables[qobject]
        self.validation_callbacks.remove(canHandleModification)
        self.effective_callbacks.remove(handleModification)

    def pre_modify(self):
        self.backup = self.cfg.serialize()

    def revert(self):
        assert self.backup is not None, 'Did you call pre_modify() before?'
        self._importSerialized(self.backup)

    def post_modify(self):
        assert self.cfg is not None, \
        "Do not call this function unless you really modified cfg. I which case you should have done a setCfg(cfg) once before"

        self.resetModels()

        if self._modificationAuthorized():
            self._propagate()
        #    self.pre_modify()
            valid = True
        else:
            self.revert()
            self.emit(SIGNAL('cancelled'))
            valid = False

        self.passed_args = []
        return valid

    def _importSerialized(self, serialized):
        try:
            self.cfg = self.deserialize(serialized)
        except Exception, err:
            self.logger.writeError(err)
        self.resetModels()

    def _modificationAuthorized(self):
        for callback in self.validation_callbacks:
            result = callback()
            if not isinstance(result, bool):
                passed_args = result[1:]
                result = result[0]
            else:
                passed_args = NOARG
            if not result:
                return False
            self.passed_args.append(passed_args)
        return True

    def _propagate(self):
        #Not catching exceptions.
        #This is a candidate for a transaction, later.
        #Simple code for now
        for index, callback in enumerate(self.effective_callbacks):
            arg = self.passed_args[index]
            if arg is NOARG:
                callback()
            else:
                callback(*arg)

    def setCfg(self, serialized):
        self._importSerialized(serialized)
        try:
            self.pre_modify()
        except Exception, err:
            self.logger.writeError(err)
        else:
            self.emit(SIGNAL('reset'))

    def getCfg(self):
        return self.cfg

    def index(self, model_name, pyobject):
        model = self.models.get(model_name)
        if model is None:
            raise ValueError("Unhandled model: %s" % model_name)

        if isinstance(pyobject, PersistentID):
            for index in xrange(model.rowCount()):
                item = model.item(index)
                data = item.data()
                if pyobject.unique_id == data.toPyObject().unique_id:
                    return index

        for index in xrange(model.rowCount()):
            item = model.item(index)
            data = item.data()
            if pyobject == data.toPyObject():
                return index
        return -1

    def item(self, model_name, index, text=False):
        model = self.models.get(model_name)
        if model is None:
            raise ValueError("Unhandled model: %s" % model_name)

        if index == -1:
            return None

        item = model.item(index)

        if text:
            return item.data().toPyObject(), item.text()
        return item.data().toPyObject()

