Introduction
============

TryFinally class is an helper to implement a try/except block with Deferred
objects: ::

    prepare()
    try:
        execute()
    finally:
        cleanup()

Pseudo-code of TryFinally: ::

    def tryFinally(value):
        try:
            if prepare:
                value = prepare(value, ...)
            if cleanup:
                try:
                    value = apply(value, ...)
                    value = cleanup(value, ...)
                except Exception, err:
                    cleanup(err, ...)
            else:
                value = apply(value, ...)
            return value
        except Exception, err:
            if error:
                error(err)
            else:
                raise


Preparation
===========

Definition of our callbacks for the examples: ::

    >>> def lock(value, error=False):
    ...     print "lock"
    ...     if error:
    ...         raise ValueError("lock error")
    ...     return "locked"
    ...
    >>> def apply(value, error=False):
    ...     print "apply"
    ...     if error:
    ...         raise ValueError("apply error")
    ...     return "applied"
    ...
    >>> def unlock(value, error=False):
    ...     print "unlock"
    ...     if error:
    ...         raise ValueError("unlock error")
    ...     return "unlocked"
    ...
    >>> def displayError(failure):
    ...     err = failure.value
    ...     print "DEFER ERROR: %s" % err
    ...     return None
    ...


Normal case (no error)
======================

Most simple example, just a function call: ::

    >>> from nucentral.common.defer import TryFinally
    >>> t = TryFinally(apply)
    >>> d = t.execute(4)
    apply

Same example with a prepare and the finally block: ::

    >>> t = TryFinally(apply)
    >>> t.setPrepare(lock)
    >>> t.setFinally(unlock)
    >>> d = t.execute(4)
    lock
    apply
    unlock


With errors
===========

Error on lock()
---------------

::

    >>> t = TryFinally(apply)
    >>> t.setPrepare(lock, error=True)
    >>> t.setFinally(unlock)
    >>> t.setError(displayError)
    >>> d = t.execute(4)
    lock
    DEFER ERROR: lock error

apply() and unlock() are not called.

Error on apply
--------------

::

    >>> t = TryFinally(apply, error=True)
    >>> t.setPrepare(lock)
    >>> t.setFinally(unlock)
    >>> t.setError(displayError)
    >>> d = t.execute(4)
    lock
    apply
    unlock
    DEFER ERROR: apply error

unlock() is called even the apply error.

Error on unlock()
-----------------

::

    >>> t = TryFinally(apply)
    >>> t.setPrepare(lock)
    >>> t.setFinally(unlock, error=True)
    >>> t.setError(displayError)
    >>> d = t.execute(4)
    lock
    apply
    unlock
    DEFER ERROR: unlock error

Error on apply() *and* unlock()
-------------------------------

Worst case: ::

    >>> t = TryFinally(apply, error=True)
    >>> t.setPrepare(lock)
    >>> t.setFinally(unlock, error=True)
    >>> t.setError(displayError)
    >>> d = t.execute(4)
    lock
    apply
    unlock
    DEFER ERROR: unlock error

As Python does with classic try/finally block, the apply error is lost because
of the unlock error.

