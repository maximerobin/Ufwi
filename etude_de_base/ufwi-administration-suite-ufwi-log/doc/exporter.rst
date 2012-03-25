                                Data exporter

Abstract
--------

In a NuCentral network, one is the master and others are slaves. Communication
is made with the *multisite_transport* component. See the NuCentral
documentation for more information.

It is so possible to call NuLog services from master.

An other way is to use NuLog to centralize data on the master NuCentral. The
Exporter feature is designed to do that.

How to use it
-------------

You may have at least two NuCentral which are the NuLog module loaded.

On Slave
~~~~~~~~

Configure the *export_period* variable (can be done on the NuLog-QT frontend) to
an other value than 0.

On Master
~~~~~~~~~

TODO

Algorithm
---------

The most part of work is done on slave.

On Slave
~~~~~~~~

Storage:
- lastsync: int
  timestamp of list synchronization.
- export_period: int
  period in seconds between each synchronization.
- rotation_period: int
  period in seconds between each table rotation.
- master: string
  master id

Every export_period:
  - if lastsync < now + rotation_period:
        warning
  - if lastsync > now - export_period:
        leave
  - else:
        delta = [lastsync; lastsync+export_period[
        sql_dump(delta) -> file
        md5, sha1, sha256, size = meta(file)

        http_publisher.add(file)
        status = master.send(url, md5, sha1, sha256, size)

        if status == OK:
            lastsync += export_period

On Master
~~~~~~~~~

Master waits for the service call, then do:

file = http.getfile(url)
if check(file, md5, sha1, sha256, size):
    sql_insert(file)
    slave.send(OK)
else:
    slave.send(NOT OK)

