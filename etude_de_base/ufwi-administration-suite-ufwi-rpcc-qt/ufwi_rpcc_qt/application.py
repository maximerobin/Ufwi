
"""
Copyright (C) 2009-2011 EdenWall Technologies

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
"""

from sys import stderr
from os import path
from sys import argv, exit, stdout
from optparse import OptionParser
from logging import (StreamHandler, getLogger, error, debug,
    DEBUG, INFO, ERROR)

from PyQt4.QtGui import QApplication
from PyQt4.QtCore import QResource

from ufwi_rpcd.common.logger import createColoredFormatter
from ufwi_rpcd.common.i18n import tr, set_translate_func
from ufwi_rpcc_qt.i18n import setup_locale, getTranslateFunc, load_qt_locale
from ufwi_rpcc_qt.auth_window import AuthWindow

def create_options_parser():
    parser = OptionParser(usage="%prog [options]")
    parser.add_option('-u', '--username',
        help=tr("Username for Rpcd authentication"),
        type="str", default=None)
    parser.add_option('-p', '--password',
        help=tr("Password for Rpcd authentication"),
        type="str", default=None)
    parser.add_option('--host',
        help=tr("Rpcd server hostname or IP address"),
        type="str", default=None)
    parser.add_option('--port',
        help=tr("Rpcd server port"),
        type="int", default=None)
    parser.add_option('--cleartext',
        help=tr("Use cleartext protocol instead of default secure (TLS)"),
        action="store_true", default=False)
    parser.add_option('--secure',
        help=tr("Use secure (TLS) protocol"),
        action="store_true", default=False)
    parser.add_option('--streaming-port',
        help=tr("UDP streaming port"),
        type="int", default=None)
    parser.add_option('--verbose', '-v',
        help="Enable verbose mode (use INFO log level, default: ERROR)",
        action="store_true", default=False)
    parser.add_option('--debug',
        help="Enable debug mode (use DEBUG log level, default: ERROR)",
        action="store_true", default=False)
    return parser

def parse_options(create_options=None):
    parser = create_options_parser()
    if create_options:
        create_options(parser)
    options, arguments = parser.parse_args()
    if arguments:
        parser.print_help()
        exit(1)
    if options.debug:
        options.verbose = True
    return options

def create_application(resource=None, locale=None, debug=False):
    app = QApplication(argv)
    translate = getTranslateFunc(app)
    if debug:
        def translate_check_types(message, comment="", value=-1):
            if not isinstance(message, str):
                raise TypeError("tr() message type must be str, not %s" % type(message).__name__)
            if not isinstance(comment, str):
                raise TypeError("tr() comment type must be str, not %s" % type(comment).__name__)
            if not isinstance(value, (int, long)):
                raise TypeError("tr() value type must be int or long, not %s" % type(value).__name__)
            return translate(message, comment, value)
        set_translate_func(translate_check_types)
    else:
        set_translate_func(translate)
    load_qt_locale(app)
    setup_locale(app, "ufwi_rpcd")
    setup_locale(app, "ufwi_rpcd_edenwall")
    if resource:
        load_resource(resource)
    if locale:
        setup_locale(app, locale)
    # load common resources
    load_resource('edenwall.rcc')
    return app

def setup_logging(options):
    if options.debug:
        level = DEBUG
    elif options.verbose:
        level = INFO
    else:
        level = ERROR
    logger = getLogger()
    logger.setLevel(level)

    formatter = createColoredFormatter(stdout, display_date=options.debug)
    handler = StreamHandler(stdout)
    handler.setLevel(level)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def create_ufwi_rpcd_application(name, resource=None, locale=None,
create_options=None, release=None):
    """
    Create a Rpcd client application:
     - name: application identifier, short string in lower case
     - resource: filename of the resources, see load_resource()
     - name: name of the locales, see setup_locale()
     - create_options: callback to create more command line options, call
       create_options(parser) where parser is an optparse.OptionParser object,
       see parse_options()
    """
    # Parse command line options and setup the logging module
    options = parse_options(create_options)
    setup_logging(options)

    # Create the application
    app = create_application(resource, locale, options.debug)
    app.options = options

    # Create Rpcd client
    client = AuthWindow(options=app.options).get_client(name, client_release=release)
    if not client:
        print >>stderr, tr("Abort authentication")
        exit(1)
    return app, client

def load_resource(filename):
    search_paths = ('.', 'tools', '/usr/share/ufwi-rpcc-qt/resources')
    for p in search_paths:
        fullpath = path.join(p,filename)
        ok = QResource.registerResource(fullpath)
        if not ok:
            continue
        debug("Load resource file: %s" % fullpath)
        return True
    error("Unable to load resource file: %s" % filename)
    return False

