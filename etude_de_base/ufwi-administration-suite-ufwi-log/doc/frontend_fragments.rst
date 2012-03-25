*******************
Data representation
*******************

.. section-numbering::
.. contents::

Introduction
============

This article only treats on the NuLog 3's Qt frontend.

The Fetcher/View model
======================

A fragment is described by a (among others) *fetcher* and a *view*. When NuLog
is trying to update a fragment, firstly it calls the fetcher, and then it sends
data to the view which shows them.

Fetchers
--------

The fetcher is a class which must implements the following methods:

        * **__init__(self, fragment, args, client)**
        * **fetch(self)**
        * **getArgs(self)**

It can have others methods to be used with a specific view. Here a list of some
examples:

        * **count(self)**
        * **kill(self, id)**
        * …

There is a fetcher for each backend, for example one for NuLog Backend, one for
the NuConntrack, one for nuauth_command, etc.


Views
-----

A view must be derived from the ufwi_log.clients.qt.views.base.BaseFragmentView
class and a QWidget.

A fragment have a list of available views. Each view have to call themself the
given fetcher to get data.

The object is directly added in the container (a QFrame in the QDockWidget).

Filters
=======



Data Representation
===================
