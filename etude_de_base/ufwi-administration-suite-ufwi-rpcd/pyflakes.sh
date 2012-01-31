#!/bin/bash
pyflakes $(find -name "*.py") \
 | grep -v "__init__.*imported but unused" \
 | grep -v "ufwi-rpcd/python/" \
 | grep -v "redefinition of unused"
