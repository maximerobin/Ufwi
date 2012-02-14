-- This is used to describe the SQL schema
-- Please annotate all tables (and/or columns id needed) with the
--   version it was first introduced
CREATE TABLE version(
	_version varchar(10),
	_format varchar(10)
);

INSERT INTO version (_version,_format) VALUES ('2.0','2.0');

-- version 2.0
CREATE TABLE acl (
	_id integer PRIMARY KEY AUTOINCREMENT UNIQUE NOT NULL,
	_group varchar(256),
	_role varchar(128),
	_host varchar(128)
);


