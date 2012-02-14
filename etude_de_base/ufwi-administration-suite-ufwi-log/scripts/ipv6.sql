-- MySQL dump 10.10
--
-- Host: localhost    Database: ufwi_log
-- ------------------------------------------------------
-- Server version	5.0.24a-Debian_9-log

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `cache_task`
--

DROP TABLE IF EXISTS `cache_task`;
CREATE TABLE `cache_task` (
  `state` int(1) default NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

--
-- Table structure for table `last_update`
--

DROP TABLE IF EXISTS `last_update`;
CREATE TABLE `last_update` (
  `timestamp` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

--
-- Table structure for table `offenders`
--

DROP TABLE IF EXISTS `offenders`;
CREATE TABLE `offenders` (
  `ip_addr` binary(16) NOT NULL,
  `first_time` datetime default NULL,
  `last_time` datetime default NULL,
  `count` int(10) default NULL,
  PRIMARY KEY  (`ip_addr`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

--
-- Table structure for table `tcp_ports`
--

DROP TABLE IF EXISTS `tcp_ports`;
CREATE TABLE `tcp_ports` (
  `tcp_dport` smallint(5) unsigned NOT NULL default '0',
  `first_time` datetime default NULL,
  `last_time` datetime default NULL,
  `count` int(10) default NULL,
  PRIMARY KEY  (`tcp_dport`),
  KEY `last_time` (`last_time`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

--
-- Table structure for table `udp_ports`
--

DROP TABLE IF EXISTS `udp_ports`;
CREATE TABLE `udp_ports` (
  `udp_dport` smallint(5) unsigned NOT NULL default '0',
  `first_time` datetime default NULL,
  `last_time` datetime default NULL,
  `count` int(10) default NULL,
  PRIMARY KEY  (`udp_dport`),
  KEY `last_time` (`last_time`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

--
-- Table structure for table `ulog`
--

DROP TABLE IF EXISTS `ulog`;
CREATE TABLE `ulog` (
  `id` int(10) unsigned NOT NULL auto_increment,
  `raw_mac` varchar(80) default NULL,
  `oob_time_sec` int(10) unsigned default NULL,
  `oob_time_usec` int(10) unsigned default NULL,
  `oob_prefix` varchar(32) default NULL,
  `oob_mark` int(10) unsigned default NULL,
  `oob_in` varchar(32) default NULL,
  `oob_out` varchar(32) default NULL,
  `ip_saddr` binary(16) default NULL,
  `ip_daddr` binary(16) default NULL,
  `ip_protocol` tinyint(3) unsigned default NULL,
  `ip_tos` tinyint(3) unsigned default NULL,
  `ip_ttl` tinyint(3) unsigned default NULL,
  `ip_totlen` smallint(5) unsigned default NULL,
  `ip_ihl` tinyint(3) unsigned default NULL,
  `ip_csum` smallint(5) unsigned default NULL,
  `ip_id` smallint(5) unsigned default NULL,
  `ip_fragoff` smallint(5) unsigned default NULL,
  `tcp_sport` smallint(5) unsigned default NULL,
  `tcp_dport` smallint(5) unsigned default NULL,
  `tcp_seq` int(10) unsigned default NULL,
  `tcp_ackseq` int(10) unsigned default NULL,
  `tcp_window` smallint(5) unsigned default NULL,
  `tcp_urg` tinyint(4) default NULL,
  `tcp_urgp` smallint(5) unsigned default NULL,
  `tcp_ack` tinyint(4) default NULL,
  `tcp_psh` tinyint(4) default NULL,
  `tcp_rst` tinyint(4) default NULL,
  `tcp_syn` tinyint(4) default NULL,
  `tcp_fin` tinyint(4) default NULL,
  `udp_sport` smallint(5) unsigned default NULL,
  `udp_dport` smallint(5) unsigned default NULL,
  `udp_len` smallint(5) unsigned default NULL,
  `icmp_type` tinyint(3) unsigned default NULL,
  `icmp_code` tinyint(3) unsigned default NULL,
  `icmp_echoid` smallint(5) unsigned default NULL,
  `icmp_echoseq` smallint(5) unsigned default NULL,
  `icmp_gateway` int(10) unsigned default NULL,
  `icmp_fragmtu` smallint(5) unsigned default NULL,
  `pwsniff_user` varchar(30) default NULL,
  `pwsniff_pass` varchar(30) default NULL,
  `ahesp_spi` int(10) unsigned default NULL,
  `timestamp` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
  `state` smallint(6) unsigned default NULL,
  `end_timestamp` datetime default NULL,
  `start_timestamp` datetime default NULL,
  `username` varchar(30) default NULL,
  `user_id` smallint(5) unsigned default NULL,
  `client_os` varchar(100) default NULL,
  `client_app` varchar(256) default NULL,
  `packets_in` int(10) default NULL,
  `packets_out` int(10) default NULL,
  `bytes_in` int(10) default NULL,
  `bytes_out` int(10) default NULL,
  UNIQUE KEY `id` (`id`),
  KEY `index_id` (`id`),
  KEY `timestamp` (`timestamp`),
  KEY `ip_saddr` (`ip_saddr`),
  KEY `udp_dport` (`udp_dport`),
  KEY `tcp_dport` (`tcp_dport`),
  KEY `oob_time_sec` (`oob_time_sec`),
  KEY `user_id` (`user_id`)
) ENGINE=MyISAM AUTO_INCREMENT=739 DEFAULT CHARSET=latin1;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `ip_saddr` binary(16) NOT NULL,
  `socket` int(10) unsigned NOT NULL,
  `user_id` int(10) unsigned default NULL,
  `username` varchar(30) default NULL,
  `start_time` datetime default NULL,
  `end_time` datetime default NULL,
  `os_sysname` varchar(40) default NULL,
  `os_release` varchar(40) default NULL,
  `os_version` varchar(100) default NULL,
  KEY `socket` (socket),
  KEY `user_id` (`user_id`),
  KEY `username` (`username`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

--
-- Table structure for table `usersstats`
--

DROP TABLE IF EXISTS `usersstats`;
CREATE TABLE `usersstats` (
  `user_id` smallint(5) unsigned NOT NULL default '0',
  `username` varchar(30) default NULL,
  `bad_conns` int(10) unsigned NOT NULL default '0',
  `good_conns` int(10) unsigned NOT NULL default '0',
  `first_time` datetime default NULL,
  `last_time` datetime default NULL,
  PRIMARY KEY  (`user_id`),
  KEY `username` (`username`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

