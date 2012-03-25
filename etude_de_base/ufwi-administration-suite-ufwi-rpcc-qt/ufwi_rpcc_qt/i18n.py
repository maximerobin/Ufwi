"""
Copyright (C) 2007-2011 EdenWall Technologies
Written by Pierre Chifflier <p.chifflier AT inl.fr>

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

from PyQt4.QtCore import QTranslator, QLocale, QLibraryInfo, QCoreApplication
from logging import debug, error
from os.path import join as path_join

def get_language():
    return QLocale.system().name()

def setup_locale(application, name, language=None, format="%s.%s"):
    """
    Load the translation for the current user locale.
    The name argument is the file name without the suffix (eg. ".fr.qm").
    So use the name "ufwi_rpcd" to load "ufwi_rpcd.fr.qm".
    """
    # Add language as suffix
    if not language:
        language = get_language()
        if not language:
            # No locale: do nothing
            return True
    filename = format % (name, language)

    translator = QTranslator(application)
    if filename.startswith(":"):
        ret = translator.load(filename)
        if ret:
            application.installTranslator(translator)
            debug("Load locale from resources: %s" % filename)
            return True
    else:
        for directory in ('.', '/usr/share/ufwi_rpcd/i18n'):
            ret = translator.load(filename, directory)
            if not ret:
                continue
            debug("Load locale file: %s" % path_join(directory, filename))
            application.installTranslator(translator)
            return True
    error("Unable to load translation file: %s" % filename)
    return False

def getTranslateFunc(application):
    def translate(text, comment, value):
        return unicode(application.translate("@default", text, comment, QCoreApplication.UnicodeUTF8, value))
    return translate

def load_qt_locale(app):
     translator = QTranslator(app)
     language = get_language()
     directory = QLibraryInfo.location(QLibraryInfo.TranslationsPath)
     translator.load("qt_" + language, directory)
     app.installTranslator(translator)

