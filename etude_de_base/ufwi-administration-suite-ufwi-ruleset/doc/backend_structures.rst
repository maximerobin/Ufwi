+++++++++++++++++++++++++
NuFace backend structures
+++++++++++++++++++++++++

Motivations of immutable objects
================================

Because all actions are undoable in the backend, we choosed to use immutable
objects. Most actions store two versions of an object. To apply the action, the
old object is removed in the object set (eg. Resources) and the new object is
added in the object set. To unapply, it's the same in the reverse order (remove
the new object and add the old object).


Problem of object references
============================

The problem of immutable objects is that we have to keep all objects updated.
If an ACL uses a protocol and the protocol is modified, we have to create a new
version of the ACL with a reference to the new protocol. This job is done
by ObjectLibrary.on_replace().

Result: when a protocol is modified, one or more ACLs will be updated too.

