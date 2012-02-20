*************
User settings
*************

.. section-numbering::
.. contents::

Introduction
============

The NuLog Qt user settings are storred with the NuCentral's config module.

The way used to store data (files or SQL database or anything else) isn't
important here. The config module needs named sections with key/values pairs.

Sections types
==============

In NuLog, we may want to store several types of “objects” in sections. To
differentiate each kind of sections, we prefix them with a “type ID”::

        regexp = ([A-Z]):(.*)

Fragments
---------

Prefixed with "F:", this kind of object describes a fragment in ufwi_log, with its
type, title, arguments, views, etc.

Pages
-----

This represents a page in NuLog. It contains a title, a list of fragments,
information about the displayed layout with Qt, etc.

The prefix is "V:" (for historical reasons).

Special
-------

This is a special kind of objects we can call “singleton”, because it is used by
objects with don't need several instances. The name is used to represent the
real type of object it is.
The prefix is "S:"

Links
~~~~~

The “Links” singleton describes all relations between all data type and pages.
Each key is a data type name (ip_saddr, tcp_port, etc.), and value is a list of
pages names.
