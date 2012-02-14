---
--- Copyright(C) 2009 INL
--- Written by Romain Bignon <romain AT inl.fr>
---
--- This program is free software; you can redistribute it and/or modify
--- it under the terms of the GNU General Public License as published by
--- the Free Software Foundation, version 3 of the License.
---
--- This program is distributed in the hope that it will be useful,
--- but WITHOUT ANY WARRANTY; without even the implied warranty of
--- MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
--- GNU General Public License for more details.
---
--- You should have received a copy of the GNU General Public License
--- along with this program; if not, write to the Free Software
--- Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
---
--- $Id$
---

--
-- Cleanup
--

DROP VIEW IF EXISTS view_ufwi_log;
DROP VIEW IF EXISTS view_insert_ulog2;
DROP VIEW IF EXISTS view_insert_nufw;
DROP VIEW IF EXISTS ulog;

ALTER TABLE ulog2 DROP COLUMN firewall;
ALTER TABLE ulog2 DROP COLUMN timestamp;

DROP TRIGGER IF EXISTS ulog_cache ON ulog2;
DROP TRIGGER IF EXISTS nufw_cache ON nufw;

--
-- EW Columns
--
ALTER TABLE ulog2 ADD COLUMN firewall varchar(50) default '';
ALTER TABLE ulog2 ADD COLUMN timestamp integer NOT NULL default EXTRACT(epoch FROM now());
CREATE INDEX ulog2_timestamp ON ulog2(timestamp);
CREATE INDEX ulog2_oob_time_sec ON ulog2(oob_time_sec);

-- Update ulog2 view with new column
CREATE OR REPLACE VIEW ulog AS
        SELECT * FROM ulog2;

--
-- Views
--

-- View to show all packets with optionnally nufw culumns
CREATE OR REPLACE VIEW view_ufwi_log AS
        SELECT * FROM ulog LEFT JOIN nufw ON ulog._id = nufw._nufw_id;

-- Views used by ulogd2 to insert rows
CREATE OR REPLACE VIEW view_insert_ulog2 AS
        SELECT _id, oob_time_sec, oob_time_usec, oob_hook, oob_prefix, oob_mark, oob_in, oob_out, oob_family, ip_saddr_str, ip_daddr_str, ip_protocol, ip_tos, ip_ttl, ip_totlen,
        ip_ihl, ip_csum, ip_id, ip_fragoff, tcp_sport, tcp_dport, tcp_seq, tcp_ackseq, tcp_window, tcp_urg, tcp_urgp, tcp_ack, tcp_psh, tcp_rst, tcp_syn, tcp_fin, udp_sport, udp_dport,
        udp_len, icmp_type, icmp_code, icmp_echoid, icmp_echoseq, icmp_gateway, icmp_fragmtu, icmpv6_type, icmpv6_code, icmpv6_echoid, icmpv6_echoseq, icmpv6_csum, raw_type,
        mac_str, mac_saddr_str, mac_daddr_str, oob_protocol, raw_label, sctp_sport, sctp_dport, sctp_csum
        FROM ulog2;

CREATE OR REPLACE VIEW view_insert_nufw AS
    SELECT _id, oob_time_sec, oob_time_usec, oob_hook, oob_prefix, oob_mark, oob_in, oob_out, oob_family, ip_saddr_str, ip_daddr_str,
                ip_protocol, ip_tos, ip_ttl, ip_totlen, ip_ihl, ip_csum, ip_id, ip_fragoff, tcp_sport, tcp_dport, tcp_seq,
                tcp_ackseq, tcp_window, tcp_urg, tcp_urgp, tcp_ack, tcp_psh, tcp_rst, tcp_syn, tcp_fin, udp_sport, udp_dport, udp_len,
                icmp_type, icmp_code, icmp_echoid, icmp_echoseq, icmp_gateway, icmp_fragmtu, icmpv6_type, icmpv6_code, icmpv6_echoid, icmpv6_echoseq,
                icmpv6_csum, raw_type, mac_saddr_str, mac_daddr_str, raw_label, sctp_sport, sctp_dport, sctp_csum, username as nufw_user_name,
                user_id as nufw_user_id, client_os as nufw_os_name, client_app as nufw_app_name
    FROM ulog LEFT JOIN nufw ON ulog._id = nufw._nufw_id;

--
-- Insert function
--

CREATE OR REPLACE FUNCTION INSERT_NUFW(
                IN _oob_time_sec integer,
                IN _oob_time_usec integer,
                IN _oob_hook integer,
                IN _oob_prefix varchar(32),
                IN _oob_mark integer,
                IN _oob_in varchar(32),
                IN _oob_out varchar(32),
                IN _oob_family integer,
                IN _ip_saddr_str inet,
                IN _ip_daddr_str inet,
                IN _ip_protocol integer,
                IN _ip_tos integer,
                IN _ip_ttl integer,
                IN _ip_totlen integer,
                IN _ip_ihl integer,
                IN _ip_csum integer,
                IN _ip_id integer,
                IN _ip_fragoff integer,
                IN _tcp_sport integer,
                IN _tcp_dport integer,
                IN _tcp_seq bigint,
                IN _tcp_ackseq bigint,
                IN _tcp_window integer,
                IN _tcp_urg boolean,
                IN _tcp_urgp integer ,
                IN _tcp_ack boolean,
                IN _tcp_psh boolean,
                IN _tcp_rst boolean,
                IN _tcp_syn boolean,
                IN _tcp_fin boolean,
                IN _udp_sport integer,
                IN _udp_dport integer,
                IN _udp_len integer,
                IN _icmp_type integer,
                IN _icmp_code integer,
                IN _icmp_echoid integer,
                IN _icmp_echoseq integer,
                IN _icmp_gateway integer,
                IN _icmp_fragmtu integer,
                IN _icmpv6_type integer,
                IN _icmpv6_code integer,
                IN _icmpv6_echoid integer,
                IN _icmpv6_echoseq integer,
                IN _icmpv6_csum integer,
                IN _raw_type integer,
                IN _mac_saddr_str macaddr,
                IN _mac_daddr_str macaddr,
                IN _raw_label integer,
                IN _sctp_sport integer,
                IN _sctp_dport integer,
                IN _sctp_csum integer,
                IN _username varchar(30),
                IN _user_id integer,
                IN _client_os varchar(100),
                IN _client_app varchar(256)
        )
RETURNS bigint AS $$
DECLARE
        _id bigint;
BEGIN
        INSERT INTO ulog2 (oob_time_sec, oob_time_usec, oob_hook, oob_prefix, oob_mark,
                           oob_in, oob_out, oob_family, ip_saddr_str, ip_daddr_str, ip_protocol,
                           ip_tos, ip_ttl, ip_totlen, ip_ihl, ip_csum, ip_id, ip_fragoff,
                           tcp_sport, tcp_dport, tcp_seq, tcp_ackseq, tcp_window, tcp_urg,
                           tcp_urgp, tcp_ack, tcp_psh, tcp_rst, tcp_syn, tcp_fin, udp_sport,
                           udp_dport, udp_len, icmp_type, icmp_code, icmp_echoid, icmp_echoseq,
                           icmp_gateway, icmp_fragmtu, icmpv6_type, icmpv6_code, icmpv6_echoid,
                           icmpv6_echoseq, icmpv6_csum, raw_type, mac_saddr_str, mac_daddr_str,
                           raw_label, sctp_sport, sctp_dport, sctp_csum)
              VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,
                      $21,$22,$23,$24,$25,$26,$27,$28,$29,$30,$31,$32,$33,$34,$35,$36,$37,
                      $38,$39,$40,$41,$42,$43,$44,$45,$46,$47,$48,$49,$50,$51);

        IF _user_id IS NOT NULL THEN
            INSERT INTO nufw (_nufw_id, username, user_id, client_os, client_app)
                   VALUES (currval('ulog2__id_seq'), _username, _user_id, _client_os, _client_app);
        END IF;

        _id := currval('ulog2__id_seq');
        RETURN _id;
END
$$ LANGUAGE plpgsql SECURITY INVOKER;


--
-- Squid logs
--

DROP SEQUENCE IF EXISTS squid__id_seq;
CREATE SEQUENCE squid__id_seq;

DROP TABLE IF EXISTS squid;
CREATE TABLE squid (
  _id bigint PRIMARY KEY UNIQUE NOT NULL DEFAULT nextval('squid__id_seq'),
  timestamp integer default NULL,
  elapsed integer default NULL,
  ip_saddr inet default NULL,
  state varchar(50) default NULL,
  code integer default NULL,
  _size integer default NULL,
  method varchar(50) default NULL,
  url varchar(256) default NULL,
  protocol varchar(10) default NULL,
  domain varchar(256) default NULL,
  username varchar(30) default NULL,
  filetype varchar(30) default NULL
) WITH (OIDS=FALSE);

--
-- Triggers
--


-- tables
DROP TABLE IF EXISTS apps_stats;
CREATE TABLE apps_stats (
  firewall varchar(50),
  client_app varchar(256) PRIMARY KEY,
  first_time integer,
  last_time integer,
  dropped integer,
  accepted integer,
  UNIQUE (firewall, client_app)
) WITH (OIDS=FALSE);

CREATE UNIQUE INDEX apps_stats_unique ON apps_stats(firewall, client_app);
CREATE INDEX apps_stats_first_time ON apps_stats(first_time);
CREATE INDEX apps_stats_last_time ON apps_stats(last_time);

DROP TABLE IF EXISTS hosts_stats;
CREATE TABLE hosts_stats (
  firewall varchar(50),
  ip_saddr_str inet PRIMARY KEY,
  first_time integer,
  last_time integer,
  dropped integer,
  accepted integer
) WITH (OIDS=FALSE);

CREATE UNIQUE INDEX hosts_stats_unique ON hosts_stats(firewall, ip_saddr_str);
CREATE INDEX hosts_stats_first_time ON hosts_stats(first_time);
CREATE INDEX hosts_stats_last_time ON hosts_stats(last_time);

DROP TABLE IF EXISTS users_stats;
CREATE TABLE users_stats (
  firewall varchar(50),
  user_id integer PRIMARY KEY,
  username varchar(30),
  first_time integer,
  last_time integer,
  dropped integer,
  accepted integer
) WITH (OIDS=FALSE);

CREATE UNIQUE INDEX users_stats_unique ON users_stats(firewall, user_id, username);
CREATE INDEX users_stats_first_time ON users_stats(first_time);
CREATE INDEX users_stats_last_time ON users_stats(last_time);

-- functions
CREATE OR REPLACE FUNCTION update_cache() RETURNS TRIGGER AS $ulog_cache$
BEGIN
    IF NEW.ip_saddr_str IS NOT NULL
    THEN
        IF NEW.raw_label = 0 THEN
            BEGIN
                INSERT INTO hosts_stats VALUES(NEW.firewall, NEW.ip_saddr_str, NEW.oob_time_sec, NEW.oob_time_sec, 1, 0);
            EXCEPTION WHEN UNIQUE_VIOLATION THEN
                UPDATE hosts_stats SET dropped = dropped + 1, last_time = NEW.oob_time_sec WHERE firewall = NEW.firewall AND ip_saddr_str = NEW.ip_saddr_str;
            END;
        ELSE
            BEGIN
                INSERT INTO hosts_stats VALUES(NEW.firewall, NEW.ip_saddr_str, NEW.oob_time_sec, NEW.oob_time_sec, 0, 1);
            EXCEPTION WHEN UNIQUE_VIOLATION THEN
                UPDATE hosts_stats SET accepted = accepted + 1, last_time = NEW.oob_time_sec WHERE firewall = NEW.firewall AND ip_saddr_str = NEW.ip_saddr_str;
            END;
        END IF;
    END IF;
    RETURN NEW;
END;
$ulog_cache$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION update_nufw_cache() RETURNS TRIGGER AS $nufw_cache$
DECLARE
    t_row ulog2%ROWTYPE;
BEGIN
    SELECT * FROM ulog2 INTO t_row WHERE _id = NEW._nufw_id;

    IF t_row.raw_label = 0
    THEN
        BEGIN
            INSERT INTO users_stats VALUES(t_row.firewall, NEW.user_id, NEW.username, t_row.oob_time_sec, t_row.oob_time_sec, 1, 0);
        EXCEPTION WHEN UNIQUE_VIOLATION THEN
            UPDATE users_stats SET dropped = dropped + 1, last_time = t_row.oob_time_sec WHERE firewall = t_row.firewall AND user_id = NEW.user_id AND username = NEW.username;
        END;
        BEGIN
            INSERT INTO apps_stats VALUES(t_row.firewall, NEW.client_app, t_row.oob_time_sec, t_row.oob_time_sec, 1, 0);
        EXCEPTION WHEN UNIQUE_VIOLATION THEN
            UPDATE apps_stats SET dropped = dropped + 1, last_time = t_row.oob_time_sec WHERE firewall = t_row.firewall AND client_app = NEW.client_app;
        END;
    ELSE
        BEGIN
            INSERT INTO users_stats VALUES(t_row.firewall, NEW.user_id, NEW.username, t_row.oob_time_sec, t_row.oob_time_sec, 0, 1);
        EXCEPTION WHEN UNIQUE_VIOLATION THEN
            UPDATE users_stats SET accepted = accepted + 1, last_time = t_row.oob_time_sec WHERE firewall = t_row.firewall AND user_id = NEW.user_id AND username = NEW.username;
        END;
        BEGIN
            INSERT INTO apps_stats VALUES(t_row.firewall, NEW.client_app, t_row.oob_time_sec, t_row.oob_time_sec, 0, 1);
        EXCEPTION WHEN UNIQUE_VIOLATION THEN
            UPDATE apps_stats SET accepted = accepted + 1, last_time = t_row.oob_time_sec WHERE firewall = t_row.firewall AND client_app = NEW.client_app;
        END;
    END IF;
    RETURN NEW;
END;
$nufw_cache$ LANGUAGE plpgsql;

CREATE TRIGGER ulog_cache BEFORE INSERT ON ulog2
    FOR EACH ROW EXECUTE PROCEDURE update_cache();
CREATE TRIGGER nufw_cache BEFORE INSERT ON nufw
    FOR EACH ROW EXECUTE PROCEDURE update_nufw_cache();

--
-- Authorizations
--



