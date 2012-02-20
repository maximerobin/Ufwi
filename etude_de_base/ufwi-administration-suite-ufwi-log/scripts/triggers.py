#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Copyright (C) 2007-2011 EdenWall Technologies
Written by Romain Bignon <romain AT inl.fr>

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

$Id$
"""

#########################
# HOW TO USE THIS SCRIPT
###
# When you create some netfilters rules, the only
# thing to know what is an ACCEPTED or a DROPPED
# packet is the log prefix.
#
# You can tell to this script what word used in
# your log prefix can be used to switch the raw_label
# of packet to 0 (drop).
#
# For NuFW packets, raw_label is correctly setted.
###
# Usage:
#          ./triggers [--drop <drop prefix>] | mysql -ulogin -ppass table
#
###

from sys import exit, stderr, argv

def main():
    # Parse command line options
    if (len(argv) != 2) or (argv[1] not in ('mysql', 'pgsql')):
        print >>stderr, "usage: %s (mysql|pgsql)" % argv[0]
        exit(1)
    dbtype = argv[1]

    # Create options
    options = {}
    if dbtype == 'mysql':
        options['match_regex'] = 'REGEXP'
    else:
        options['match_regex'] = '~'

    # Create the trigger
    print """
DROP TRIGGER IF EXISTS update_cache;

DELIMITER |

CREATE TRIGGER update_cache BEFORE INSERT ON ulog
    FOR EACH ROW BEGIN

        /* If raw_label is null, it is because this is a netfilter log.
         */
        IF NEW.raw_label IS NULL
        THEN
            /* Drop (D), Unauthenticated drop (U) or REJECT (R) */
            IF NEW.oob_prefix %(match_regex)s '^[IOF][0-9]+[DURdr]:'
            THEN
                SET NEW.raw_label = 0;
            END IF;
            /* Accept (A), prefix "I5A:http to internet" */
            IF NEW.oob_prefix %(match_regex)s '^[IOF][0-9]+[Aa]:'
            THEN
                SET NEW.raw_label = 2;
            END IF;
        END IF;

        /* Dropped packets */
        IF NEW.raw_label=0
        THEN

            /* Offenders */
            INSERT INTO offenders VALUES (NEW.ip_saddr, NOW(), NOW(), 1)
                ON DUPLICATE KEY UPDATE count = count + 1, last_time = NOW();

            /* Update TCP stats */
            IF NEW.ip_protocol = 6 THEN
                INSERT INTO tcp_ports VALUES (NEW.tcp_dport, NOW(), NOW(), 1)
                    ON DUPLICATE KEY UPDATE count = count + 1, last_time = NOW();
            END IF;

            /* Update UDP stats */
            IF NEW.ip_protocol = 17 THEN
                INSERT INTO udp_ports VALUES (NEW.udp_dport, NOW(), NOW(), 1)
                    ON DUPLICATE KEY UPDATE count = count + 1, last_time = NOW();
            END IF;

            /* Update user stats (number of dropped packets) */
            IF NEW.user_id IS NOT NULL THEN
                INSERT INTO usersstats VALUES (NEW.user_id, NEW.username, 1, 0,  NOW(), NOW())
                    ON DUPLICATE KEY UPDATE bad_conns = bad_conns + 1, last_time = NOW();
            END IF;

        /* Allowed packets */
        ELSE
            /* USERSSTATS (allowed) */
            IF NEW.user_id IS NOT NULL THEN
                /* We don't add entry in usersstats if there isn't already a line
                 * for this user_id.
                 * Ask Regit why :)
                 */
                /* Do not update timestamp, because we use it only for bad packets.. */
                UPDATE usersstats SET good_conns = good_conns + 1 WHERE user_id = NEW.user_id;
            END IF;
        END IF;
    END;
|

DELIMITER ;
""" % options

if __name__ == '__main__':
    main()
