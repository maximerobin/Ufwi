#!/bin/bash
DIR=$(dirname $0)
set -x
$DIR/tools/ufwi_rpcd_client -u admin -p admin --host localhost --debug "$@"
