#!/bin/sh

databases=`LANG=en_US.UTF8 sudo -u postgres psql -l`
occurrence=`echo $databases |grep -c 'edenaudit'`
if test $occurrence == 0 ; then
    echo "database edenaudit not found. Not deleting"
else
    echo "database edenaudit already exists. Deleting."
    lang=en_us.utf8 sudo -u postgres psql -c "DROP DATABASE edenaudit;"
fi

users=`LANG=en_US.UTF8 sudo -u postgres psql -c "\du"`
occurrence=`echo $users |grep -c 'edenaudit_owner'`
if test $occurrence == 0 ; then
    echo "user edenaudit_owner not found. Not deleting"
else
    echo "user edenaudit_owner found. Deleting"
    lang=en_us.utf8 sudo -u postgres psql -c "DROP USER edenaudit_owner;"
fi
occurrence=`echo $users |grep -c 'edenaudit'`
if test $occurrence == 0 ; then
    echo "user edenaudit not found. Not deleting"
else
    echo "user edenaudit found. Deleting"
    lang=en_us.utf8 sudo -u postgres psql -c "DROP USER edenaudit;"
fi

