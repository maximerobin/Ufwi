# -*- coding: utf-8 -*-
"""
Copyright (C) 2008-2011 EdenWall Technologies
Written by:
François Toussenel <f.toussenel AT inl.fr>
Feth AREZKI <farezki AT inl.fr>
$Id$
"""

from ufwi_rpcd.common.unicode_stdout import installUnicodeStdout
installUnicodeStdout()

def _get_window_class():
        from main_window import MainWindow
        return MainWindow
