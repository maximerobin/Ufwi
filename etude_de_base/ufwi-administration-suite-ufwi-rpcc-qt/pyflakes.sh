#!/bin/sh
pyflakes $(find -name "*.py")|grep -v "__init__.*imported but unused"
