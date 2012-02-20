from IPy import IP
from urlparse import urlparse

def ip_in_ldapuri(ldapuri):
    for item in ldapuri.split():
        #It's not a problem if we replace something even in the FQDN, as we are
        #looking for numeric values
        #The problem is that urlparse does not support ldap(s)
        item = item.replace('ldap', 'http', 1)
        parsed = urlparse(item)
        if parsed.scheme == 'https':
            try:
                IP(parsed.hostname)
            except (ValueError, AttributeError):
                continue
            else:
                return True
    return False

def has_ldaps(ldapuri):
    return any(item.startswith("ldaps://") for item in ldapuri.split())

