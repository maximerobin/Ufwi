
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

from ufwi_rpcd.common import tr

APP_TITLE = tr('Central management')

MULTISITE_COLUMNS = {
    # Main tab
    'name' :                    tr('Firewall name'),
    'firewall_name' :           tr('Firewall name'),
    'global_status' :           tr('Global status'),
    'dropped_packets' :         tr('Dropped packets'),
    'current_template' :        tr('Current template'),
    'last_seen' :               tr('Last connected'),
    'bandwidth_in' :            tr('Inbound traffic'),
    'bandwidth_out' :           tr('Outbound traffic'),
    'nuauth_users' :            tr('Identified users'),
    'error' :                   tr('Error'),


    # Tempaltes view
    'nuface_template' :         tr('Available templates'),
    'template_edition_time' :   tr('Edition date'),
    'links_validity' :          tr('Links validity'),
    'current_template' :        tr('Current template'),
    'template_version' :        tr('Template version'),
    'nuface_status' :           tr('Status'),
    'send_rules' :              tr('Send new rules'),
    'revision' :                tr('Version'),
    'edenwall_type' :           tr('Edenwall type'),

    # Update view
    'nuconf_update_filepath' :  tr('Update to send'),
    'nuconf_update_browse' :    '',
    'nuconf_update_send' :      tr('Send update'),
    'nuconf_update_status' :    tr('Status'),

    # Scheduler view
    'schedule_start' :          tr('Start date'),
    'schedule_rate' :           tr('Repeat rate'),
    'schedule_stop_on_success': tr('Stop on success'),
    'task_type':                tr('Type'),
    'task_description' :        tr('Description'),
    'task_status' :             tr('Status'),
    'task_modify' :             tr('Reschedule/Delete'),

    # Monitoring
    'ha_mode' :                 tr('HA type'),
    'monitoring_load' :         tr('CPU load'),
    'monitoring_mem' :          tr('Memory'),
    'hdd__' :                   tr('Root partition'),
    'hdd__var' :                tr('Var partition'),
    'hdd__tmp' :                tr('Temporary partition'),
    'hdd__usr' :                tr('Software partition'),
    'hdd__var_lib_postgresql' : tr('Log database partition'),
    'hdd__var_lib_ldap' :       tr('Directory partition'),
    'hdd__var_log' :            tr('System logs partition'),
    'hdd__var_spool' :          tr('Spool partition'),
    'hdd__var_tmp' :            tr('Temporary partition'),
    }

