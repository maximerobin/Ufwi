
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

LDAPSEARCH_RETURN_CODES = {
    0: tr("(0x00) LDAP_SUCCESS: the operation was successful."),
    1: tr("(0x01) LDAP_OPERATIONS_ERROR: sent by Directory Server for general errors "
        "encountered by the server when processing the request."),
    2: tr("(0x02) LDAP_PROTOCOL_ERROR: the search request did not comply with the LDAP "
        "protocol. Directory Server may send this error code if it could not sort "
        "the search results or could not send sorted results."),
    3: tr("(0x03) LDAP_TIMELIMIT_EXCEEDED: sent by Directory Server if the search "
        "exceeded the maximum time specified by the -l option."),
    4: tr("(0x04) LDAP_SIZELIMIT_EXCEEDED: sent by Directory Server if the search "
        "found more results than the maximum number of results specified by the -z option."),
    10: tr("(0x0a) LDAP_REFERRAL: sent by Directory Server if the given base DN is an "
        "entry not handled by the current server and if the referral URL identifies a different server to handle the entry."),
    11: tr("(0x0b) LDAP_ADMINLIMIT_EXCEEDED: sent by Directory Server if the search found more results than the limit specified by the lookthroughlimit directive in the slapd.conf configuration file. If not specified in the configuration file, the default limit is 5000."),
    21: tr("(0x15) LDAP_INVALID_SYNTAX: sent by Directory Server if your substring filter contains no value for comparison."),
    32: tr("(0x20) LDAP_NO_SUCH_OBJECT: sent by Directory Server if the given base DN does not exist and if no referral URLs are available."),
    50: tr("(0x32) LDAP_INSUFFICIENT_ACCESS: sent by Directory Server if the DN used for authentication does not have permission to read from the directory."),
    53: tr("(0x35) LDAP_UNWILLING_TO_PERFORM: sent by Directory Server if the database is read-only."),
    81: tr("(0x51) LDAP_SERVER_DOWN: the LDAP server did not receive the request or the connection to the server was lost."),
    82: tr("(0x52) LDAP_LOCAL_ERROR: an error occurred when receiving the results from the server."),
    83: tr("(0x53) LDAP_ENCODING_ERROR: the request could not be BER-encoded."),
    84: tr("(0x54) LDAP_DECODING_ERROR: an error occurred when decoding the BER-encoded results from the server."),
    85: tr("(0x55) LDAP_TIMEOUT: the search exceeded the time specified by the -l option."),
    87: tr("(0x57) LDAP_FILTER_ERROR: an error occurred when parsing and BER-encoding a search filter specified on the command-line or in a filter file."),
    89: tr("(0x59) LDAP_PARAM_ERROR: one of the options or parameters is invalid."),
    90: tr("(0x5a) LDAP_NO_MEMORY: memory cannot be allocated as needed."),
    91: tr("(0x5b) LDAP_CONNECT_ERROR: the specified hostname or port is invalid."),
    92: tr("(0x5c) LDAP_NOT_SUPPORTED: the -V 2 option is needed to access a server that only supports LDAP v2."),
}

