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

from IPy import IP
from random import randint, choice
import time

pgsql = True
ipv6 = True

if pgsql:
    import psycopg2
else:
    import MySQLdb

class Traffic:

    usernames = [('romain', 1000), ('pollux', 1001), ('ft', 1002), ('lodesi', 1003),
                 ('eric', 1004), ('gryzor', 1005), ('olivier', 1006), ('sandra', 1007),
                 ('naotemp', 1008), ('misc', 1009), ('haypo', 1010), ('saispo', 1011),
                 ('romain', 1000), ('romain', 1000), ('misc', 1009), ('sandra', 1007)]
    if ipv6:
        ips = ['::fd5e:ea85:4552:ef1e', '::ff56:f85a:f654:85ef', '::fde5:165e:5f65:f4e1',
            '::eafb:fce5:b00b:cafe', '::1337:6969:b173:aefb', '::fe64:2321:aaee:bbbb',
            '::4e6f:44ea:f4e6:ccde', '::6562:1658:489:5654',  '::aefb:ffea:ffea:feaa',
            '::eafb:fce5:b00b:cafe', '::fe64:2321:aaee:bbbb']
        d_ips=['::f56d:f65e:f54f:ff78', '::f51a:d66e:f49e:cfea', '::fe6a:fe6f:5615:5485']
    else:
        ips = ['1.32.5.58', '51.5.15.6', '4.8.9.22', '1.2.3.4']
        d_ips = ['8.2.6.4', '54.66.12.5', '15.74.112.1', '15.26.15.212']
    OSs = ['Linux', 'Windows', 'OpenBSD', 'Mac OS X']
    apps = ['/usr/bin/ssh', '/usr/bin/firefox', '/usr/bin/irssi', '/usr/bin/nmap', '/usr/bin/peerfuse', '/usr/bin/bzflag',
            '/usr/local/bin/frozzen-bubble', '/usr/bin/konqueror']
    prefixs = [['DROPPED', 'FWD:5:DROPPED', 'IN:8:DROPPED'],
               '',
               '',
               'AUTHENTICATED',
               'AUTHENTICATED']
    ports = [21,22,23,80,8080,6667,6666,5130,5461,113,447,69]


    def __init__(self, host, user, passwd, db):
        if pgsql:
            self.conn = psycopg2.connect (host = "localhost",
                                        user = "ulog",
                                        password = "ulog",
                                        database = "ulog")
        else:
            self.conn = MySQLdb.connect (host = "localhost",
                                        user = "ufwi_log",
                                        passwd = "pupuce",
                                        db = "ulog")


    def sendto_db(self, msg):
        cursor = self.conn.cursor()
        cursor.execute(msg)
        self.conn.commit()
        cursor.close()

    def insert_new_user(self, user):
        ip = choice(self.ips)
        print '*** User %s connected from %s' % (user[0], ip)
        self.sendto_db('INSERT INTO users (ip_saddr, socket, user_id, username, start_time, os_sysname) ' \
                  'VALUES (%s, %d, %d, \'%s\', Now(), \'%s\')'
                    % (self.str2ip(ip), randint(0,500), user[1], user[0], choice(self.OSs)))

    def update_users(self, user=None):

        ext = ''
        if user:
            ext = ' WHERE username = \'%s\'' % user[0]
            print '*** User %s disconnected' % user[0]
        else:
            print '*** All users are disconnected!'

        self.sendto_db('UPDATE users SET end_time = Now()%s' % ext)

    def update_packets(self):
        print '*** All connections closed'
        self.sendto_db('UPDATE ulog SET raw_label = 3 WHERE raw_label = 4')

    def insert_packet(self):

        username = None
        if randint(0,1):
            username = choice(self.usernames)

        ip = choice(self.ips)
        d_ip = choice(self.d_ips)
        sport = randint(10000,65530)
        dport = choice(self.ports)
        raw_label = choice([0, 3, 4])
        os = None
        app = None
        if not username:
            prefix = 'UNAUTHENTICATED ' + (raw_label and 'ACCEPT' or 'DROP')
            if randint(0,1):
                ip = choice(self.d_ips)
                d_ip = choice(self.ips)
                sport = choice(self.ports)
                dport = randint(10000,65530)
        else:
            prefix = self.prefixs[raw_label]
            if isinstance(prefix, list):
                prefix = choice(prefix)
            os = choice(self.OSs)
            app = choice(self.apps)

        proto = choice(['tcp', 'udp'])

        print '[%s] Packet stored from %s[%s]:%d to %s:%d: %s' % (proto, ip, username and username[0] or 'NotLogged',
                                                                  sport, d_ip, dport, prefix)

        self.sendto_db("INSERT INTO ulog (oob_time_sec, oob_prefix, oob_in, oob_out, ip_saddr, ip_daddr, ip_protocol, %s_sport, " \
                                        "%s_dport, raw_label, username, user_id, client_os, client_app, raw_mac, packets_in, packets_out," \
                                        "bytes_in, bytes_out) " \
                        "VALUES (%d, '%s', 'eth0', 'eth1', %s, %s, 6, %d, %d, %d, %s, %s, %s, %s, '%s', %d, %d, %d, %d)"
                        % (proto, proto, int(time.mktime(time.localtime())), prefix, self.str2ip(ip), self.str2ip(d_ip),
                            sport, dport, raw_label, (username and ("'" + username[0] + "'") or 'NULL'), (username and username[1] or 'NULL'),
                            (os and ("'%s'" % os) or "NULL"), (app and ("'%s'" % app) or 'NULL'),
                            '11:22:33:44:55:66:00:11:22:33:44:55:00:11', 512, 1024, randint(32,1024), randint(32,2048)))

    def str2ip(self, string):
        if pgsql:
            return "'%s'" % string
        else:
            if ipv6:
                return 'LPAD(0x%X, 16, 0x00)' % IP(string).int()
            else:
                return IP(string).int()

def main():
    try:
        traffic = Traffic(host = "localhost",
                            user = "ufwi_log",
                            passwd = "pupuce",
                            db = "ulog")
        for user in traffic.usernames:
            traffic.insert_new_user(user)

        while 1:
            time.sleep(randint(0, 999) / 1000.0)

            if not randint(0,3):
                traffic.update_users(choice(traffic.usernames))

            if not randint(0,3):
                traffic.insert_new_user(choice(traffic.usernames))

            if not randint(0,4):
                traffic.update_packets()

            traffic.insert_packet()

    except KeyboardInterrupt:
        traffic.update_users()

if __name__ == '__main__':
    main()
