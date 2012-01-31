#!/bin/sh

users=`LANG=en_US.UTF8 sudo -u postgres psql -c "\du"`
occurrence=`echo $users |grep -c 'edenaudit'`
if test $occurrence == 0 ; then
    echo "user edenaudit not found. Creating"
    lang=en_us.utf8 sudo -u postgres psql -c "CREATE USER edenaudit WITH PASSWORD '1234';"
else
    echo "user edenaudit already exists. NOT creating"
fi
occurrence=`echo $users |grep -c 'edenaudit_owner'`
if test $occurrence == 0 ; then
    echo "user edenaudit_owner not found. Creating"
    lang=en_us.utf8 sudo -u postgres psql -c "CREATE USER edenaudit_owner WITH PASSWORD '1234';"
else
    echo "user edenaudit_owner already exists. NOT creating"
fi

databases=`LANG=en_US.UTF8 sudo -u postgres psql -l`
occurrence=`echo $databases |grep -c 'edenaudit'`
if test $occurrence == 0 ; then
    echo "database edenaudit not found. Creating"
    lang=en_us.utf8 sudo -u postgres psql < create_database.sql
    lang=en_us.utf8 sudo -u postgres psql -d edenaudit < create_tables.sql
else
    echo "database edenaudit already exists. NOT creating."
fi

