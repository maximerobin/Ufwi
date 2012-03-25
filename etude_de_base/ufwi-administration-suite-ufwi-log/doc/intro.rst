************
Introduction
************

.. section-numbering::

Presentation
============

NuLog 3 is is a log analysis for `NetFilter`_ and `NuFW`_.

There are two main components:

ufwi_log.core
----------

This is the backend of Nulog3. All operations will be done here.

ufwi_log.clients.qt
----------------

This is the `Qt`_ frontend for NuLog. It can be a stand-alone application
(run it from ufwi_log-qt/ufwi_log-qt.py application), or a part of a complex
application (for example, the EdenWall Administation Suite).

It gets data from ufwi_log.core, but can interact with other kind of components,
like `NuConntrack`_, `nuauth_command`_, etc.

NuCentral
=========

Nulog3 is designed to be a part of `NuCentral`_.

NuCentral is an application used to plug components on it, and
each components can call a service from an other component.

Goal of NuCentral is, when a component is on a local NuCentral (where
my component is plugin) or a distant NuCentral, that my component will
doesn't care about. Call will be cloaking.

NuCentral uses the `Twisted`_ framework.

To have more informations about NuCentral, see the `NuCentral`_ documentation.

Documentations list
===================

 * `Tables`_
 * `Frontend fragments`_
 * `User settings`_


Vocabulary
=======================

* **Page**: This is a window in a frontend which contains fragments.
* **Fragment**: This is a box on the page which contains data.
* **Fragment type**: A fragment is constitued by a fragment type and some other arguments.
* **Arguments**: Each fragment type can accept some arguments to build the returned data.
* **Filters**: Special arguments used to filter on fragment data.
* **View**: From the data fetched from backend for a fragment type, the frontend can use one or several views to show them.
* **Docks**: Fragments are this Qt boxes which can be moved, tabbed, etc.

.. _Tables: tables.html
.. _Data representation: data_representation.html
.. _Frontend fragments: frontend_fragments.html
.. _User settings: user_settings.html

.. _Twisted: http://twistedmatrix.com/
.. _NetFilter: http://www.netfilter.org/
.. _NuFW: http://www.nufw.org/
.. _NuCentral: http://software.inl.fr/trac/wiki/NuCentral
.. _Qt: http://trolltech.com/products
.. _NuConntrack: http://software.inl.fr/trac/wiki/NuConntrack
.. _nuauth_command: http://www.nufw.org/

