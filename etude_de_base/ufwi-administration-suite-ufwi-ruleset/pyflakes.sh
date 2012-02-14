#!/bin/bash
find -name "*.pyc"|xargs -r rm
echo 1>&2 "run pyflakes..."
pyflakes $(find -name "*.py") scripts/nuface \
    | egrep -v '__init__.*imported but unused' \
    | egrep -v 'setup.*redefinition of unused .setup. from '
echo 1>&2 "run pyflakes... done"

