***************
Table fragments
***************

.. section-numbering::
.. contents::

Backend (ufwi_log.core)
====================

The TableBase class
--------------------

In the NuLog backend, all data are fetched from a SQL database, so the default
representation of that data is tables. Each kind of table is a fragment type.

All tables have to be derivated from the **TableBase** class or upper.

List of tables
~~~~~~~~~~~~~~

As a static member of the NulogCore class (ufwi_log.py), the table list is defined
in the **tables** dictionnary::

        tables = {
            'TCPTable':          table.TCPTable,
            'UDPTable':          table.UDPTable,
            'IPsrcTable':        table.IPsrcTable,
            'IPdstTable':        table.IPdstTable,
            'UserTable':         table.UserTable,
            'PacketTable':       table.PacketTable,
            'UsersHistoryTable': table.UsersHistoryTable,
            'AppTable':          table.AppTable,
            'PacketInfo':        info.PacketInfo,
            'BadHosts':          table.BadHosts,
            'BadUsers':          table.BadUsers,
            'TrafficTable':      table.TrafficTable,
            'Stats':             table.Stats,
        }


Initialization
~~~~~~~~~~~~~~

The **__init__** method have to call firstly the TableBase constructor to
define the columns list::

        TableBase.__init__(self, table,
              ['packet_id','username','ip_saddr', 'ip_daddr',  'proto','sport',
              'dport','oob_time_sec','oob_prefix'])

Next, the **args** dictionnary attribute have to be set. This **mustn't**
contain filters::

        self.args = {'sortby': 'oob_time_sec',
                     'sort':   'DESC',
                     'limit':  30,
                     'start':  0}

Call
~~~~

When a frontend wants to fetch data from your table, the *__call__()* method
will be called.

This function receives arguments requested. The request is built with them.

To define what arguments the table can receive, and how to check if they are
valid, there are these functions:

    * **self._arg_int(args, key)**: Check if args[key] is an integer, and add it to self.args dict.
    * **self._arg_bool(args, key)**: Check if args[key] is a boolean.
    * **self._arg_in(args, key, list)**: Check if args[key] is in list (a tuple), and add it to self.args.
    * **self._arg_where(args, buffer, list)**: To create the *where* instruction, you have to pass a StringIO object
      as *buffer* variable to save in string. *list* is a dict where keys are args keys, and values are help functions.
      The following functions are available:

        - **self._arg_where_ip** to create a filter on ip. [1]_
        - **self._arg_where_REVERSEip** like *self._arg_where_ip* but used when
          bytes order is in an other endian. [1]_
        - **self._arg_where_ip_both** , like *self._arg_where_ip* but it will check for source and destination ips.
        - **self._arg_where_port** to create a filter on port. [1]_
        - **self._arg_where_proto** to create a filter on protocol.
        - **self._arg_where_state** to create a filter on packet state. [1]_
        - **self._arg_where_int** to create a filter which is an integer. [1]_
        - **self._arg_where_begin_time** to create a filter on timestamp.
        - **self._arg_where_end_time** to create a filter on timestamp.
        - **self._arg_where_like** to create the LIKE sql statment. [1]_


.. [1] These functions depend of key string. For example, _arg_where_port will create ``key = value`` string.

Here is an example::

    def __call__(self, **args):
        where = StringIO()

        # In our example, we want to display the number of dropped packets for users in the last 15 minutes
        where.write('WHERE timestamp > NOW()- INTERVAL 15 MINUTE AND (state IS NULL OR state = 0)')

        self._arg_int(args, 'limit')
        self._arg_int(args, 'start')
        self._arg_in (args, 'sortby', ('username', 'packets', 'end'))
        self._arg_in (args, 'sort',   ('DESC', 'ASC'))
        self._arg_where(args, where, {'sport': self._arg_where_port,
                                      'dport': self._arg_where_port,
                                      'proto': self._arg_where_proto
                                     })

After that check, a good idea is to call the **_sql_query** to do some sql
requests.

All SQL queries are abstracted in the **DataBase** class. This create a
compatibility with some SQL schemas and databases.

Call this method with args::

        result = self._sql_query("select_packets", where.getvalue())
        result.addCallback(self._print_result)
        return result

self._print_result is a callback of TableBase. For each line it will call a
function **self.entry_form**, empty on TableBase. But it can be overloaded like
this::

    def entry_form(self, entry):
        return (entry[0], entry[1], entry[2])

It can be used to modify an entry. For example an IP is an integer (ipv4) or a
byte (ipv6) in the SQL table. To convert it to a human-readable IP, call
self.ip2str() function to do this. See TabeBase's API.

Returned value
~~~~~~~~~~~~~~

The **TableBase** returns a XML-RPC serializable dictionary in the form::

        {'args': {'arg1': value1, 'arg2': value2, ...},
         'filters': {'filter1': fvalue1, 'filter2': fvalue2, ...},
         'columns': ['column1', 'column2', ...],
         'rowcount': int(rowcount),
         'table': [[line1col1, line1col2, ...], [line2col1, line2col2, ...], ...]
        }

The DataBase object
-------------------

The **DataBase** object is defined in the **database.py** file.

There is a base object for the standard ulog database named **Request**.
Derived objects are used for other SQL schemas, for example **TriggerRequest**.

For each tables, there are a SQL definition of each kind of database.

Frontend (ufwi_log.clients.qt)
===========================

Fragment type list
------------------

The frontend has a list of fragment types in the **fragtypes.py** file.

Each fragments are listed in the **frag_types** dictionnary. Each fragment type
is described with a FragType object.

For more information about the QT frontend's fragments management, read the
`Data representation`_ documentation.

.. _Data representation: data_representation.html
