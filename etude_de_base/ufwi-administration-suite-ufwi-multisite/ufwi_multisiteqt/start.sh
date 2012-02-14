#!/bin/bash
cd $(dirname $0)
export PYTHONPATH=$PWD/../../../edenwall-administration-suite/trunk/:$PWD/../../../nuface3/trunk/:$PYTHONPATH
./ew4-multisite-qt --debug "$@"
