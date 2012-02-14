======
NuConf
======

This documentation describes how to develop the frontend of NuConf.

Structure
---------

The frontend interface is composed of pages called modules. The pages are
accessible through a menu on the left, in the form of a tree. Each module
can be defined either in a class written by hand or in a generic way
following some specification given by the backend. The frontend asks the
backend for the menu structure.  Each item in the menu may have a full
specification of what should be inside the corresponding page, which is
the case of the System/DNS module, for instance.  The class NuConfForm
interprets the specification and takes care of the layout and
interactions with the user.  For a more complex module, like
Network/Direct nets, a class is written by hand.

The file main_window.py imports every available module listed in the menu
tree given by the backend.  Every module derives from the class
NuConfForm.

The modules are named strictly after the English name of the corresponding
item in the menu, so that they can be imported automatically according to
the menu.  The name includes the full path in the menu tree.  For
instance, the page "Direct nets" under Network is Network__Direct_nets
(replace each space with an underscore, and use two underscores as the
path separator).

Many graphical components of a module, like a widget containing a label
and a button, are factorized into functions written in the module
NuConfPageKit.  Use those as much as possible, and if something is wanted,
consider adding a new function to NuConfPageKit to create the needed
widget.  All widgets of a page are inside a scroll widget.

If you construct a layout manually, you should define sections (grouping
some controls) with a title for each, and inside each section, stack
controls using "create*" functions from NuConfPageKit.

Tracking modified state
-----------------------

When the user modifies some setting, NuConf must turn on its "modified"
state, and when the user saves the configuration, NuConf must turn it off.
The save and reset actions are disabled if NuConf is not in a modified
state.  We use stateChanged (or equivalent) kinds of signals to handle the
modified state.  Each module has a "_modified" attribute to track this
state at the module level, and the main window has one too (for save and
reset actions, and the title of the window).  The setModified method of
modules calls the setModified method of main_window.
