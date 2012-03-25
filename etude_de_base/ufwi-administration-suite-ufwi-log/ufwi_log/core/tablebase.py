# -*- coding: utf-8 -*-

"""
Copyright (C) 2007-2011 EdenWall Technologies
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

from datasource import DataSource
import time, datetime

class TableBase(DataSource):

    """
    TODO: THIS DOCSTRING IS OUT OF DATE!

    This is a table base object.
    You can call a SGDB and receive his answer in a formated table.
    Note that it is designed for SOAP calls.

    Example:

        class MyTable(TableBase):

            def __init__(self, ctx, database):
                TableBase.__init__(database)

            def __call__(self, **args):

                sort = args['sort']

                result = self._sql_query('SELECT hello, world from helloworld ORDER BY %s' % sort)

                result.addCallback(self._print_result)
                return result

            def entry_form(self, entry):

                result = (entry[0] + '_',)
                result += entry[1:]
                return result

    Usage:

        >>> table = MyTable()     # Create MyTable instance
        >>> deferred = table(**{'sort': 'hello'})    # <=> table.__call__()

        If this is a SOAP function, return deferred object, and SOAP will wait
        callback function to return it value.
        _print_result() return a dict.

    """

    columns = []
    default_args = {}

    def __init__(self, ctx, database):
        """
            @param database [DataBase] database object
            @param columns [list] list of columns _id
        """

        DataSource.__init__(self, ctx, database)
        self.table = []
        self.states = {}
        self.entries = 0
        self.rowcount = 0

        assert isinstance(self.columns, list)
        assert isinstance(self.args, dict)

    def __iter__(self):

        return self.table.__iter__()

    def entry_form(self, entry):
        """ This is a callback for each entry received by _sql_query()
        Overload this method to process a entry.

            @param entry [tuple] This is a line.

            @return [tuple]

        WARNING: tuple is an imutable object, so you HAVE to recreate another tuple
        to modify it !
        """

        return entry

    def _print_count(self, result):
        """ Callback used by a _sql_query() when I want to receive a result of a
            COUNT(*) query.
        """

        try:
            return int(result[0][0][0])
        except (TypeError, IndexError):
            return 0

    @staticmethod
    def normalize(value):
        if isinstance(value, (tuple, list)):
            lst = []
            for subvalue in value:
                lst.append(TableBase.normalize(subvalue))
            return lst
        elif value is None:
            return ''
        elif isinstance(value, datetime.datetime):
            return time.mktime(value.timetuple())
        elif isinstance(value, int) or isinstance(value, long):
            return value
        else:
            return unicode(value)

    def _print_result(self, result):
        """ Callback of _sql_query() when I receive a result from SGDB
            @param result [array of tuple]

            @return [dict] If called by XML-RPC, client will receive result of this function
                            ret['args'] = dict with all arguments used for this request
                            ret['filters'] = dict with all filters
                            ret['columns'] = list of column titles
                            ret['rowcount'] = integer number of lines (it doesn't consider 'start' and 'limit')
                            ret['table'] = 2D array with table resulted
        """

        self.rowcount = result[1]
        result = result[0]

        for entry in result:
            t = self.entry_form(entry)
            line = []
            if not isinstance(t, list) or not isinstance(t, tuple):
                self.table.append(TableBase.normalize(t))
            else:
                for i in t:
                    if isinstance(i, str):
                        i = unicode(i, 'utf-8')

                    line.append(TableBase.normalize(i))
                self.table.append(line)

        return {'args': self.args,
                'filters': self.filters,
                'columns': self.columns,
                'rowcount': self.rowcount,
                'table': self.table,
                'states': self.states,
               }

    def _remove_column(self, name):
        try:
            self.columns.remove(name)
        except:
            pass

    def _add_column(self, name):
        self.columns.append(name)

class InfoBase(TableBase):
    """ This class is herited from TableBase and has just only one specific overloaded function """


    def _print_result(self, result):
        """ Callback of _sql_query() when I receive a result from SGDB
            In this function, we will create a dict to associate key and value.
            @param result [array of tuple]

            @return [dict] dictionnary with all key/values results
        """

        rowcount = result[1]
        result = result[0]

        if rowcount == 0:
            return None

        info = {}
        line = self.entry_form(result[0])

        for key, value in zip(self.columns, line):
            if isinstance(value, tuple) or isinstance(value, list):
                lst = []
                for v in value:
                    if v is None:
                        lst += [u'']
                    else:
                        lst += [unicode(v)]
                value = lst
            elif value == None:
                value = u''
            else:
                value = unicode(value)
            info[key] = value

        return info



