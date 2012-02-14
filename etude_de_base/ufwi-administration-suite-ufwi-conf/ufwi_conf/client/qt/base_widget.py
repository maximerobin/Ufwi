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

class BaseWidget(object):
    # Abstract class attributes: child classes have to define them
    COMPONENT = None
    LABEL = None
    REQUIREMENTS = None
    ICON = None

    # If IDENTIFIER is not set, COMPONENT is used for the identifier
    IDENTIFIER = None

    def __init__(self):
        if self.COMPONENT is None:
            raise ValueError("%s.COMPONENT is not set" % self.__class__.__name__)
        if self.LABEL is None:
            raise ValueError("%s.LABEL is not set" % self.__class__.__name__)
        if self.REQUIREMENTS is None:
            raise ValueError("%s.REQUIREMENTS is not set" % self.__class__.__name__)

    @staticmethod
    def get_calls():
        # return a tuple (or list) of service calls
        # eg. [('CORE', 'getComponentList')]
        return tuple()

    def unload(self):
        pass

    def isValid(self):
        return True

    def saveConf(self, message=None):
        pass

    # FIXME: Create a base setModified() method,
    # reuse maybe NuConfForm.setModified()

    #--- abstract methods ---------------------------------

    @abstractmethod
    def isModified(self):
        pass

