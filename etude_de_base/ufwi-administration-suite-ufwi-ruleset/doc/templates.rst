================
NuFace templates
================

Templates
---------

It's possible to create a ruleset template with incomplete ACL rules. Example:

    Allow users from the LAN network to access to the SMTP server

where the LAN network and SMTP server are not defined. The networks will be
defined later when the ruleset template is used in new ruleset.

Association dictionary
----------------------

The association between a network template and the concrete object is done in a
dictionary. Example: ::

   Network "LAN": address=10.8.2.0/24
   Host "SMTP": address=10.8.2.5

You can not change the object type. Example of invalid association: ::

   Host "SMTP": address=10.3.0.0/16

Mandatory and optional rules
----------------------------

You choose if a (ACL or NAT) rule using template objects can be ignored or not
in iptables/LDAP if a least one template object (used by the rule) is not
defined. Example:

    Allow users from the LAN network to access to the Squid server

You can choose between ignore the rule and raise an error if the Squid server
is not defined using the "optional" field of an rule.

Tests:

 - Mandatory rule (optional=false): raise an error if the rule is not fully
   defined
 - For an optional rule, behaviour depends on the state of the variable in the
   dictionary:

   * Undefined:

     - in the graphical interface: raise an error to force to  user to choose
       (define the object or ignore the rule)
     - non interactive mode: ignore the rule (but display a warning)

   * Ignore: ignore the rule
   * Defined: generate the rule

Summary:

 * A rule has a boolean option: optional
 * Each variable in the dictionary has three states: undefined, ignore, defined

