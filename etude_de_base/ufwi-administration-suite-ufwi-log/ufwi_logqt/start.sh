#!/bin/bash
#
# Launcher for ufwi_log_qt
#

ROOT=$(cd $(dirname $0)/..; pwd -P)

# FIXME: nuwidgets is no more used
# export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:$ROOT/ufwi_log/client/qt/nuwidgets/"
export PYTHONPATH="$PYTHONPATH:$ROOT"
$ROOT/ufwi_logqt/ufwi_log_qt -u admin -p admin --debug "$@"
