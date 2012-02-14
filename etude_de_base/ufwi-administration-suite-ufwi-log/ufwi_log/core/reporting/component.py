# -*- coding: utf-8 -*-

"""
Copyright (C) 2009-2011 EdenWall Technologies
Written by Romain Bignon <romain AT inl.fr>

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

from cStringIO import StringIO
from base64 import b64encode, b64decode
from copy import deepcopy

from ufwi_rpcd.backend import tr, Component, RpcdError
from ufwi_rpcd.backend.exceptions import ConfigError
from ufwi_rpcd.common.error import NULOG
from ufwi_rpcd.common.defer import gatherResults, succeed

from .report import Report
from ufwi_log.core.errors import NULOG_REPORTING_ALREADY_EDITING, \
                              NULOG_REPORTING_NOT_EDITING

class NoReportOpened(RpcdError):
    def __init__(self, *args, **kwargs):
        RpcdError.__init__(self, NULOG, NULOG_REPORTING_NOT_EDITING, *args, **kwargs)

class AlreadyEditingReport(RpcdError):
    def __init__(self, *args, **kwargs):
        RpcdError.__init__(self, NULOG, NULOG_REPORTING_ALREADY_EDITING, *args, **kwargs)

class Task(object):
    def __init__(self, task_interval, title, interval, logo, scenario, filters):
        self.task_interval = task_interval
        self.title = title
        self.logo = logo
        self.scenario = scenario
        self.filters = filters

class ReportingComponent(Component):

    NAME = "reporting"
    VERSION = "3.0-2"
    API_VERSION = 1
    REQUIRES = set(('ufwi_log',))
    ROLES = {'ufwi_log_read':         set(('new', 'newPage', 'append', 'appendTopOfThePop', 'build', 'demo'))}

    default_conf = {
        }

    def init(self, ufwi_rpcd_core):
        self.ufwi_rpcd_core = ufwi_rpcd_core

        self.conf = self.default_conf

        for key in self.conf.keys():
            try:
                self.conf[key] = self.ufwi_rpcd_core.config_manager.get('ufwi_log', 'reporting', key)
            except ConfigError, err:
                self.debug("Get configuration error: %s" % err)

    # ------------- decorators ---

    def report_opened(func):
        def f(self, ctx, *args, **kwargs):
            session = ctx.getSession()
            try:
                report = session['report']
            except KeyError:
                raise NoReportOpened(tr('Please create a report first'))
            else:
                return func(self, ctx, report, *args, **kwargs)
        f.__name__ = func.__name__
        f.__doc__ = func.__doc__
        return f

    # ------------- services ---

    def lambda_callService(self, *args, **kwargs):
        return lambda x: self.ufwi_rpcd_core.callService(*args, **kwargs)

    def service_plan(self, ctx, task_interval, title, interval, logo, scenario, filters):
        task = Task(task_interval, title, interval, logo, scenario, filters)

    def service_new(self, ctx, title, enterprise, interval, logo, scenario, filters):
        session = ctx.getSession()
        if 'report' in session:
            raise AlreadyEditingReport(tr("You are already in a report edition"))

        report = Report(title, enterprise, interval, b64decode(logo))
        session['report'] = report

        d = succeed(True)
        for command in scenario:
            for args in command:
                if isinstance(args, dict):
                    # Predefined args are more prioritary than user filters.
                    saved_args = args.copy()
                    args.clear()
                    args.update(filters)
                    args.update(saved_args)
            d.addCallback(self.lambda_callService(ctx, 'reporting', *command))

        return d

    @report_opened
    def service_newPage(self, ctx, report, title, cols):
        return report.addPage(title, cols)

    @report_opened
    def service_append(self, ctx, report, title, render, table, args):
        deferred = self.ufwi_rpcd_core.callService(ctx, 'ufwi_log', 'table', table, args)
        deferred.addCallback(self.append_cb, report, title, render)
        deferred.addErrback(self.append_eb)
        return deferred

    def append_cb(self, result, report, title, render):
        return report.addGraph(title, result['columns'], result['table'], render)

    def append_eb(self, err):
        # TODO what can we do when an error happened on fragment reception?
        self.writeError(err)
        return

    @report_opened
    def service_appendTopOfThePop(self, ctx, report, title, table, args, filter, table2, args2):
        deferred = self.ufwi_rpcd_core.callService(ctx, 'ufwi_log', 'table', table, args)
        deferred.addCallback(self.appendTop_cb, ctx, report, title, filter, table2, args2)
        deferred.addErrback(self.append_eb)
        return deferred

    def appendTop_cb(self, result, ctx, report, title, filter, table2, args2):
        table = result['table']
        i = result['columns'].index(filter)
        deferreds = []
        for line in table:
            if isinstance(line[i], (list, tuple)):
                value = line[i][1]
            else:
                value = line[i]
            args2[filter] = value
            d = self.ufwi_rpcd_core.callService(ctx, 'ufwi_log', 'table', table2, args2)
            deferreds.append(d)

        return gatherResults(deferreds).addCallback(self.appendTop_cb2, report, title, result)

    def appendTop_cb2(self, subtables, report, title, result):
        if not subtables:
            return report.addGraph(title, [], [], 'table')

        table = []
        columns = set(result['columns'])
        columns = columns.union(subtables[0]['columns'])
        columns = list(columns)
        for i, section in enumerate(result['table']):
            sub = subtables[i]
            line = []
            for col in columns:
                try:
                    line.append(section[result['columns'].index(col)])
                except ValueError:
                    line.append('')
            table.append(line)
            for row in sub['table']:
                line = []
                for col in columns:
                    try:
                        line.append(row[sub['columns'].index(col)])
                    except ValueError:
                        line.append('')
                table.append(line)

        return report.addGraph(title, columns, table, 'table')

    @report_opened
    def service_build(self, ctx, report):
        buf = report.build()

        session = ctx.getSession()
        del session['report']

        return b64encode(buf.getvalue())

    def service_demo(self, ctx):
        if 'report' in ctx.getSession():
            del ctx.getSession()['report']
        d = self.ufwi_rpcd_core.callService(ctx, 'reporting', 'new', 'EmptyReport', 'blah', '', {})
        d.addCallback(lambda x: self.ufwi_rpcd_core.callService(ctx, 'reporting', 'newPage', 'Tuch it', [1,1]))
        d.addCallback(lambda x: self.ufwi_rpcd_core.callService(ctx, 'reporting', 'appendTopOfThePop',
                                            'Blahbla', 'UserTable', {'sortby': 'packets', 'limit': 5, 'raw_label': 1}, 'username',
                                                       'TCPTable', {'sortby': 'packets', 'limit': 5, 'raw_label': 1}))
        d.addCallback(lambda x: self.ufwi_rpcd_core.callService(ctx, 'reporting', 'append',
                                            'Most dropped hosts', 'table',   'IPsrcTable',
                                            {'sortby': 'packets', 'raw_label': 0}))
        d.addCallback(lambda x: self.ufwi_rpcd_core.callService(ctx, 'reporting', 'newPage', 'My tralala', [1,2]))
        d.addCallback(lambda x: self.ufwi_rpcd_core.callService(ctx, 'reporting', 'append',
                                            'Most dropped hosts', 'pie',   'IPsrcTable',
                                            {'sortby': 'packets', 'raw_label': 0}))
        d.addCallback(lambda x: self.ufwi_rpcd_core.callService(ctx, 'reporting', 'append',
                                            'Most dropped users', 'histo', 'UserTable',
                                            {'sortby': 'packets', 'raw_label': 0}))
        d.addCallback(lambda x: self.ufwi_rpcd_core.callService(ctx, 'reporting', 'append',
                                            'Most active users',  'line',  'UserTable',
                                            {'sortby': 'packets', 'raw_label': -1}))
        d.addCallback(lambda x: self.ufwi_rpcd_core.callService(ctx, 'reporting', 'build'))
        return d
