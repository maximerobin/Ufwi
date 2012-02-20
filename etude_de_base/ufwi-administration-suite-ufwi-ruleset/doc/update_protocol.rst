++++++++++++++++++++++
NuFace update protocol
++++++++++++++++++++++

Why using updates
=================

NuFace design goal is to do all checks (object consistency validation) in the
backend and the frontend is only a stupid user interface (without or with few
checks). Example: The user interface doesn't check if a protocol is already
used by an ACL on protocol deletion.

For a GUI, we have to limit window repaint and so only update the minimum
widgets (eg. only the modified ACL in the ACL list).

NuFace supports undo/redo actions on *any* action (create, delete, update any
object).

For all these reasons, NuFace backend generates a list of updates
(differences). So the frontend can update its local state and refresh the
widgets.


Presentation of the updates
===========================

Update and Updates classes are used to store the data updates.  An update has a
domain (eg. "acls") and a type (eg. "create"). See nuface/forward/action.py for
the whole list of domains and types. Updates store one or more Update objects.
An action may generates multiple updates, eg. change a resource identifier may
also update the ACLs using the resource.

Examples of updates: ::

    [("resources", "update", "DMZ")]
    [("acls-ipv4", "create", 1)]


Object libraries (eg. domain "protocols")
=========================================

Example with the protocols, but all objects works as protocols:

 * ["protocols", "create", "HTTP"] : New protocol "HTTP" created
 * ["protocols", "update", "HTTP"] : Attributes of protocol "HTTP" updated
 * ["protocols", "delete", "HTTP"] : Protocol "HTTP" deleted

See service_object[Create|Modify|Delete] in forward component.

Domains "acls" and "bichains"
=============================

Don't change the order of existing ACLs:

 * ["acls", "create", 42]: ACL #42 created (added to the end of its bichain)
 * ["acls", "update", 42]: Attributes of the ACL #42 are
   changed, but the ACL order is unchanged
 * ["acls", "delete", 42]: ACL #42 deleted

Change the ACL order and/or move an ACL from a bichain to another:

 * ["bichains", "create", (("eth0", "eth1"), 42)]: Create the new bichain
   eth0=>eth1 which now contains the ACL #42
 * ["bichains", "update", (("eth0", "eth1"), 42)]: Bichain eth0=>eth1 updated for
   the ACL #42
 * ["bichains", "delete", (("eth0", "eth1"), -1)]: Delete the bichain eth0=>eth1


See also
========

 * backend_structures.rst

