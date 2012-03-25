---
SET client_encoding = 'UTF8';

CREATE TABLE _format (
        version integer
);

INSERT INTO _format VALUES (1);


-- Create Events and Alerts Database
CREATE  TABLE alert (
        uniqueid serial,-- PRIMARY KEY,
        message text,
        category varchar(255),
        priority integer,
        acknowledged boolean,
        ack_user varchar(255),
        ack_timestamp timestamp without time zone,
        creation_timestamp timestamp without time zone,
        ack_message text,
        CONSTRAINT "alert_id_pkey" PRIMARY KEY ("uniqueid")
);


CREATE TABLE event (
        uniqueid serial  PRIMARY KEY,
        alert_uniqueid integer,
        message text,
        category varchar(255),
        ip_src varchar(50),
        ip_dst varchar(50),
        port_src integer,
        port_dst integer,
        "user" text,
        timestamp timestamp without time zone,
        used boolean,
        priority integer,
        source_key varchar(100),
        weight integer,
--        Constraint "event_id_pkey" Primary Key ("id")
        CONSTRAINT event_alert_uniqueid_fkey FOREIGN KEY (alert_uniqueid)
            REFERENCES alert (uniqueid) MATCH SIMPLE
            ON UPDATE NO ACTION ON DELETE NO ACTION
);

GRANT SELECT ON TABLE  _format to edenaudit;
GRANT SELECT, INSERT, UPDATE ON TABLE event TO edenaudit;
GRANT USAGE, UPDATE ON SEQUENCE event_uniqueid_seq TO edenaudit;
GRANT SELECT, INSERT, UPDATE ON TABLE alert TO edenaudit;
GRANT USAGE, UPDATE ON SEQUENCE alert_uniqueid_seq TO edenaudit;
