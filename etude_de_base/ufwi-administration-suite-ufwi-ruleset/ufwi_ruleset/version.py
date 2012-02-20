PACKAGE = "ufwi_ruleset"
WEBSITE = "http://www.ufwi.org/"
LICENSE = "GNU GPLv3"

# Ruleset protocol version:
# "3.0.6"
#   - Add platform library
# "3.0.5":
#   - Add moveRule() service used for rule drag & drop
# "3.0.4":
#   - Add name attribute to the user groups
#   - Create nufw.require_group_name option
#   - User group number is no more mandatory: an user group can have only a
#     name (user directory with no group number, eg. Active Directory) or only
#     a number (backward compatibility)
# "3.0.3": add type attribute to the NAT rules
# "3.0.2": create setupClient() and setFusion() services, add IPsec
#    networks. fusion argument of getObjects(), objectCreate(), ... services is
#    now optional: keep it for backward compatibility, use client value if the
#    value is not specified.
# "3.0.1": add default decisions to ACL rules
# "3.0rc": add auth_quality attribute to ACL rules
# "3.0m3": first version
#
# See also ufwi_rulesetqt/compatibility.py
VERSION = "3.0.6"
