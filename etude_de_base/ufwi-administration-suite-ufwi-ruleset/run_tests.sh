#!/bin/bash

PYTHON=python
PYTEST=/usr/bin/py.test

DIR=$(dirname $0)
cd $DIR
export PYTHONPATH=$PYTHONPATH:$DIR

# exit on errors
set -e

export PYTHONPATH=$PWD:../nuface3\
:../nucentral-multisite/qt\
:../nucentral-admin\
:../nupki\
:../nulog3\
:../nuconf\
:../nucentral\
:../nucentral-edenwall\
:../nucentral-multisite\

# show commands
set -x
set -e

$PYTHON ./test_doc.py
#PYTHONPATH="$PYTHONPATH" $SUDO $PYTHON $PYTEST -x --tb=short tests/ "$@"
#PYTHONPATH="$PYTHONPATH" $SUDO $PYTHON ./tests/apply_rules.py

