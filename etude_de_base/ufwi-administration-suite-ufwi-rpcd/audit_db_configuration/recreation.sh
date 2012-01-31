#!/bin/sh

set -e

tried_restart=0

function exiting () {
cd ${curdir}
if test $tried_restart == 0; then
	tried_restart=1
	/etc/init.d/nucentral-server start
fi
}

trap exiting EXIT INT ERR

curdir=$PWD
cd /usr/share/nucentral/audit_db_configuration
/etc/init.d/nucentral-server stop
/usr/share/nucentral/audit_db_configuration/deletion.sh
/usr/share/nucentral/audit_db_configuration/creation.sh

