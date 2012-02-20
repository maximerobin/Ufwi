#!/bin/bash -x
DIR=$(dirname $0)
export PYTHONPATH=$PYTHONPATH:$PWD
$DIR/nuface-qt -u admin -p admin --debug "$@"
