
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

class ServiceStatusValues (object):
    """
    Constant strings categorizing component types
    Explanation of statuses:
    A) the component is NOT associated to anything we can monitor
     - NOT_A_SERVICE
    B) the component is associated to something we can monitor
     - RUNNNING: the monitored service is running
     - STOPPED: the monitored service is NOT running
    C) the component is not loaded, although it is expected to be one of the
       monitoring components (status.ALL_SERVICE_MONITORING_COMP
     - NOT_LOADED
    D) the component does not implement service_status at all OR
       does not implement the full protocol of its own implementation
     - STATUS_NOT_IMPLEMENTED
    """
    __running = "RUNNING"
    __stopped = "STOPPED"
    __not_loaded = "NOT_LOADED"
    __polling = "POLLING"
    (RUNNING, STOPPED, NOT_A_SERVICE, STATUS_NOT_IMPLEMENTED, NOT_LOADED, POLLING) = \
    (__running, __stopped, "NOT_A_SERVICE", "NOT_IMPLEMENTED", __not_loaded, __polling)

    monitor_status = (__running, __stopped, __not_loaded)
