#!/bin/bash
SUDO="sudo -H"
#PYTHON="env python2.5"
TWISTED=$(which twistd)
TAC=ufwi-rpcd.tac
OPTIONS="-no -l /dev/null"
cd $(dirname $0)
if [ $# -eq 0 ]; then
    echo "Use default options: $OPTIONS"
    set -x
    $SUDO $PYTHON $TWISTED --python=$TAC $OPTIONS
else
    set -x
    $SUDO $PYTHON $TWISTED --python=$TAC "$@"
fi
