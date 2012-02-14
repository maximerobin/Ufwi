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


from ufwi_rpcd.common.recursors import gen_recursor

def _valid_type_isvalidWithMsg(parent_result, parent_method):
    if len(parent_result) != 2 \
        or not isinstance(parent_result[0], bool) \
        or  not isinstance(parent_result[1], (str, unicode)):

        raise TypeError(
            "Wrong result type produced by method %s - '%s'" %
            (parent_method, repr(parent_result))
        )

def _return_early_isValidWithMsg(parent_result):
    ok, msg = parent_result
    if not ok:
        return True
    return False

callParent_isValidWithMsg = gen_recursor(
    'callParent_isValidWithMsg',
    'isValidWithMsg',
    _valid_type_isvalidWithMsg,
    _return_early_isValidWithMsg,
    """
    This decorator will call parent's isValidWithMsg.

    It returns early if a False result is found.
    Checks that are done:
    -cannot decorate anything but isValidWithMsg methods
    -returns have to be of type (Boolean, String)
    """
    )
