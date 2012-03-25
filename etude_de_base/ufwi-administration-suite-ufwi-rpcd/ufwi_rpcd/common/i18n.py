"""
Copyright (C) 2009-2011 EdenWall Technologies
Written by Victor Stinner <victor.stinner AT inl.fr>

This file is part of NuFirewall.

 NuFirewall is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, version 3 of the License.

 NuFirewall is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with NuFirewall.  If not, see <http://www.gnu.org/licenses/>

$Id$
"""

# Translate a message to the user mother language:
#
#  - server side: do nothing (converts message to unicode). Dummy translation
#    function needed to allow Qt Linguist extract the messages.
#  - client side: use QApplication.translate() to translate the message
#    (see ufwi_rpcd.qt.i18)
#
# usage: tr("text in english")
#    or: tr("%s item(s)", '', count): plural form
#    or: tr("File", "comment"), comment is only visible for the translator
def tr(message, comment="", value=-1):
    return tr.func(message, comment, value)
def _tr_dummy(message, comment, value):
    return unicode(message)
tr.func = _tr_dummy

def set_translate_func(func):
    tr.func = func

