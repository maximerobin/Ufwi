from ufwi_rpcd.common.odict import odict

DOMAINS = (
    "resources",
    "protocols",
    "platforms",
    "user_groups",
    "applications",
    "periodicities",
    "operating_systems",
    "durations",
    "acls-ipv4",
    "acls-ipv4-chains",
    "acls-ipv4-decisions",
    "acls-ipv6",
    "acls-ipv6-chains",
    "acls-ipv6-decisions",
    "nats",
    "nats-chains",
    "custom_rules",
    "generic-links",
    "ruleset",
)
DOMAIN_ORDER = dict((domain, order) for order, domain in enumerate(DOMAINS))
DOMAINS = set(DOMAINS)

TYPES = set(("update", "create", "delete"))

class Update:
    """
    Object to notice the user interface (especially graphical interface)
    that a object changed.
    """
    def __init__(self, domain, type, *identifiers):
        if domain not in DOMAINS:
            raise ValueError("Invalid update domain: %s" % domain)
        if type not in TYPES:
            raise ValueError("Invalid update type: %s" % type)
        self.domain = domain
        self.type = type
        self.identifiers = list(identifiers)
        self.identifier_set = set(identifiers)

    def extend(self, identifiers):
        for identifier in identifiers:
            if identifier in self.identifier_set:
                continue
            self.identifiers.append(identifier)
            self.identifier_set.add(identifier)

    def __repr__(self):
        return "<Update domain=%s type=%s identifiers=%r>" % (self.domain, self.type, self.identifiers)

class Updates:
    def __init__(self, *updates):
        self.updates = []
        for update in updates:
            self.addUpdate(update)

    def add(self, domain, type, *identifiers):
        update = Update(domain, type, *identifiers)
        self.addUpdate(update)

    def addUpdate(self, new_update):
        for update in self.updates:
            if update.domain == new_update.domain \
            and update.type == new_update.type:
                update.extend(new_update.identifiers)
                return
        self.updates.append(new_update)

    def addUpdates(self, updates):
        for update in updates.updates:
            self.addUpdate(update)

    def createTuple(self):
        grouped = []
        index = 0
        while index < len(self.updates):
            update = self.updates[index]
            current_domain = update.domain
            group_updates = [(update.type, tuple(update.identifiers))]
            index += 1
            while index < len(self.updates):
                update = self.updates[index]
                if update.domain != current_domain:
                    break
                item = (update.type, tuple(update.identifiers))
                group_updates.append(item)
                index += 1
            item = (current_domain, group_updates)
            grouped.append((current_domain, group_updates))
        return grouped

    def __repr__(self):
        return "<Updates (%s)>" % ', '.join(repr(update) for update in self.updates)

    @staticmethod
    def create(update):
        if isinstance(update, Updates):
            return update
        else:
            return Updates(update)

    def __iter__(self):
        return iter(self.updates)

    def getTypes(self):
        return set(update.type for update in self.updates)

    def partialUpdate(self):
        identifiers = []
        for update in self:
            if '*' in update.identifiers:
                # ('protocols', 'update', *') means that all protocols
                # have to be refresh
                return None
            if update.type != "update":
                return None
            identifiers.extend(update.identifiers)
        return identifiers

    def getHighlightId(self):
        for update in self:
            if update.type == "delete":
                continue
            for identifier in update.identifiers:
                if isinstance(identifier, tuple):
                    # rule chain identifier
                    key, rule_id = identifier
                    if 0 < rule_id:
                        return rule_id
                else:
                    # classic identifier (an unicode string)
                    if identifier != '*':
                        return identifier
        return None

def createUpdatesOdict(all_updates):
    updates_odict = odict()
    for domain, updates_list in all_updates:
        updates = Updates()
        for update in updates_list:
            type, identifiers = update
            if domain.endswith("-chains"):
                _identifiers = []
                for chain, rule_id in identifiers:
                    if isinstance(chain, list):
                        # ['eth0', 'eth2'] => ('eth0', 'eth2')
                        chain = tuple(chain)
                    _identifiers.append((chain, rule_id))
                identifiers = _identifiers
            update = Update(domain, type, *identifiers)
            updates.addUpdate(update)
        updates_odict[domain] = updates
    return updates_odict

