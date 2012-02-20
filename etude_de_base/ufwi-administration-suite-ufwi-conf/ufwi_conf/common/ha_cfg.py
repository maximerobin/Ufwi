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

from ufwi_rpcd.common.abstract_cfg import AbstractConf
from ufwi_rpcd.common import tr
from ufwi_conf.common.ha_statuses import (ENOHA, PENDING_PRIMARY,
    PENDING_SECONDARY, SECONDARY)
from ufwi_conf.common.ha_base import haNet
from ufwi_conf.common.net_exceptions import NetCfgError
from ufwi_conf.common.net_interfaces import Interface

AUTO_FAILBACK = 'on'
PRIMARY_PORT = 54322
SECONDARY_PORT = 54323
UDP_PORT = 694

HA_LINK_STATUS = \
    NOT_REGISTERED, \
    NOT_CONNECTED, \
    CONNECTED = \
    'NOT_REGISTERED', \
    'NOT_CONNECTED', \
    'CONNECTED'

HA_STATE = ACTIVE, INACTIVE = 'ACTIVE', 'INACTIVE'

class HAConf(AbstractConf):
    """
    configuration for high availability component

    interface_id : hard label of interface
    interface_name : system name of interface
    """

    ATTRS = """
            ha_type
            interface_id
            interface_name
            primary_hostname
            """.split()

    DATASTRUCTURE_VERSION = 3

    def __init__(self, ha_type=None, interface_id=None, interface_name=None, primary_hostname=None):
        AbstractConf.__init__(self)

        self.ha_type = \
        self.interface_id = \
        self.interface_name = \
        self.primary_hostname = None

        self._setLocals(locals())

    def isValidWithMsg(self):
        """
        return None if object is valid or a tuple : ('format', ...)
        """
        if not self.ha_type in (PENDING_PRIMARY, SECONDARY, PENDING_SECONDARY, ENOHA):
            return (tr("unknow type '%s'"), unicode(self.ha_type))

def requireha(func):
    def pre_condition(interface, *args, **kwargs):
        if not interface.reserved_for_ha:
            raise NetCfgError(tr("This interface is not configured for High Availability"))
        return func(interface, *args, **kwargs)
    return pre_condition

def requirenoha(func):
    def pre_condition(interface, *args, **kwargs):
        if interface.reserved_for_ha:
            raise NetCfgError(tr(
                "Operation forbidden: this "
                "interface is configured for High Availability"
                ))
        return func(interface, *args, **kwargs)
    return pre_condition

@requirenoha
def _configureHA(interface):
    """
    primary = True or False
    """
    if not interface.canReserve():
        raise NetCfgError(tr(
            "Can not reserve this interface. "
            "Need an interface with IP not configured"
            ))
    interface.user_label = "%s: %s" % (
        interface.system_name, tr("reserved for High Availability")
        )
    interface.addNet(haNet())
    interface.reserved_for_ha = True

@requireha
def _deconfigureHA(interface):
    interface.reserved_for_ha = False
    interface.user_label = interface.system_name
    interface.nets.clear()

def configureHA(netcfg, iface):
    """
    only one interface must be configured for HA
    """
    if not isinstance(iface, Interface):
        raise NetCfgError(
            "Expected type Interface, "
            "got '%s' of type '%s' instead" % (unicode(iface), type(iface))
            )

    ha_interface = getHAInterface(netcfg)
    if ha_interface is not None:
        if ha_interface.unique_id != iface.unique_id:
            deconfigureHA(netcfg)
        else:
            # already configured
            return

    _configureHA(iface)

def deconfigureHA(netcfg):
    ha_interface = getHAInterface(netcfg)
    if ha_interface is not None:
        _deconfigureHA(ha_interface)
        return
    raise NetCfgError(
        "Cannot deconfigure HA: no HA interface is configured."
        )

def getHAInterface(netcfg):
    """
    return None or iface with ha
    """
    for iface in netcfg.iterInterfaces():
        if iface.reserved_for_ha:
            return iface
    return None


