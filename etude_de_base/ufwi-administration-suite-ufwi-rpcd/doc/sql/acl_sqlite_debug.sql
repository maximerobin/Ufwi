BEGIN TRANSACTION;
CREATE TABLE version(
	_version varchar(10),
	_format varchar(10)
);
INSERT INTO "version" VALUES('2.0','2.0');
CREATE TABLE acl (
	_id integer PRIMARY KEY AUTOINCREMENT UNIQUE NOT NULL,
	_group varchar(256),
	_role varchar(128)
);
INSERT INTO "acl" (_group, _role) VALUES('admin','multisite_write');
INSERT INTO "acl" (_group, _role) VALUES('admin','log_read');
INSERT INTO "acl" (_group, _role) VALUES('admin','log_write');
INSERT INTO "acl" (_group, _role) VALUES('admin','pki_write');
INSERT INTO "acl" (_group, _role) VALUES('admin','ruleset_write');
INSERT INTO "acl" (_group, _role) VALUES('admin','multisite_read');
INSERT INTO "acl" (_group, _role) VALUES('admin','conf_read');
INSERT INTO "acl" (_group, _role) VALUES('admin','conf_write');
INSERT INTO "acl" (_group, _role) VALUES('admin','rpcd_debug');
INSERT INTO "acl" (_group, _role) VALUES('admin','ruleset_read');
INSERT INTO "acl" (_group, _role) VALUES('admin','rpcd_admin');
INSERT INTO "acl" (_group, _role) VALUES('admin','pki_read');
INSERT INTO "acl" (_group, _role) VALUES('admin','audit_read');
COMMIT;
