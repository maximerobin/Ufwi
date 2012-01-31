#coding: utf-8
"""
Copyright(C) 2010 EdenWall Technologies
$Id$
"""
from __future__ import with_statement

from ConfigParser import SafeConfigParser
from datetime import datetime, timedelta
from collections import deque, defaultdict
from elixir import \
        Unicode, Integer, Boolean, UnicodeText, TIMESTAMP, \
        Entity, using_options, Field, OneToMany, ManyToOne
from os.path import join
from time import mktime, gmtime
from calendar import timegm

from ufwi_rpcd.backend.error import CoreError
from ufwi_rpcd.backend import Component
from ufwi_rpcd.backend import SessionError
from ufwi_rpcd.core.context import Context

from .audit_base import Connector
from .error import ALERT_ALREADY_ACK, ACK_FORBIDDEN, API_PROBLEM, DB_NO_CONNECTION

AUDIT_PARAMETERS_API = 1
AUDIT_CONF_FILE = "audit.conf"

CATEGORIES = ("authentication", "service", "spoof", "misc", "configuration", "rights", "ntp")
WEIGHT = {"authentication" : 20,
          "service" : 10,
          "spoof" : 50,
          "misc" : 20,
          "configuration" : 40,
          "rights" : 50,
          "ntp" : 50,
        }
# Priorities
PRIORITY_EVENT = 0
PRIORITY_ALERT = 1

ONE_DAY = timedelta(1)

connector = Connector.getInstance()

use_postgres = connector.db_url.startswith("postgres")
if use_postgres:
    from sqlalchemy.databases import postgres
    IPAddress = postgres.PGInet
else:
    IPAddress = Integer

def check_value(value):
    # FIXME
    if isinstance(value, list) and len(value) == 1:
        value = value[0]
    if value is None:
        return ''
    return value

class BaseAuditEvent(object):
    XMLRPC_ATTRS = 'category priority message'.split()

    def __init__(self, category, priority, message):
        if category not in CATEGORIES:
            raise ValueError("Unknown category: %s" % category)
        if priority not in (PRIORITY_EVENT, PRIORITY_ALERT):
            raise ValueError("Invalid priority: %r" % priority)
        if not isinstance(message, unicode):
            raise TypeError("The message have to be an unicode string")
        self.category = category
        self.priority = priority
        self.timestamp = timegm(gmtime())

    def exportXMLRPC(self):
        serialized = {}
        for name in BaseAuditEvent.XMLRPC_ATTRS:
            value = getattr(self, name)
            value = check_value(value)
            serialized[name] = value
        return serialized

    def __ne__(self, other):
        return not self == other

    def __eq__(self, other):
        for attr in self.XMLRPC_ATTRS:
            if getattr(self, attr) != getattr(other, attr):
                return False
        return True

_USER_INFO_TEMPLATE = u"""\


Details:
     Source IP: %s
     Source port: %s
     Cookie: %s
"""

class AuditEvent(BaseAuditEvent, Entity):
    XMLRPC_ATTRS = 'source timestamp'.split() + BaseAuditEvent.XMLRPC_ATTRS

    category = Field(Unicode(50))
    message = Field(UnicodeText)
    uniqueid = Field(Integer, primary_key=True)
    ip_src = Field(Unicode(50))
    ip_dst = Field(Unicode(50))
    port_src = Field(Integer)
    port_dst = Field(Integer)
    user = Field(Unicode(50))
    timestamp = Field(TIMESTAMP(100))
    used = Field(Boolean)
    priority = Field(Integer)
    weight = Field(Integer)

    source_key = Field(Unicode(100))

    alert = ManyToOne('CorrelatorAlert')
    using_options(
        tablename="event",
        session=connector.session,
        metadata=connector.metadata,
        order_by='-timestamp')

    attrs = """
    ip_src ip_dst timestamp user category
    used source_key
    """.split()

    @staticmethod
    def contextinfo(context, user=u'', user_cookie=u''):
        if context.isUserContext():
            user = context.user
            caller = u"User '%s'" % user

            cookie = "No cookie associated with this session"
            try:
                session = context.getSession()
            except SessionError:
                cookie = "No cookie - session killed?"
                session = None

            if session is not None:
                cookie = session.cookie
            elif len(user_cookie) > 0:
                cookie = user_cookie

            contextinfo = _USER_INFO_TEMPLATE % (
                context.user.host,
                context.user.port,
                cookie
                )
        else:
            caller = u"Component '%s'" % context.component.name
            contextinfo = u''


        return contextinfo, caller, user

    @staticmethod
    def fromACL(context, component=None, service=None):
        contextinfo, caller, user = AuditEvent.contextinfo(context)
        if component is not None:
            if service:
                message = \
                        u"%s tried to access service %s.%s and had no right to do so." % (
                        caller, component, service
                        )
            else:
                message = \
                        u"%s tried to access component %s and had no right to do so." % (
                        caller, component
                        )
        else:
            raise TypeError("You have to provide a component")

        message += contextinfo

        return AuditEvent(
            'Core',
            "service",
            message=message,
            user=user
            )

    @staticmethod
    def fromNTPSync(user_context):
        category = "ntp"
        return AuditEvent.eventFactory(user_context, category)

    @staticmethod
    def fromAclsEvent(user_context):
        category = "rights"
        return AuditEvent.eventFactory(user_context, category)

    @staticmethod
    def fromAuditConfModification(context, message):
        category = "configuration"
        return AuditEvent.eventFactory(context, category, message)

    @staticmethod
    def eventFactory(context, category, message=u'', user=u'', user_cookie=u''):
        contextinfo, caller, user = AuditEvent.contextinfo(context, user, user_cookie)
        message += caller
        message += contextinfo
        source_key = "Audit"

        return AuditEvent(
            source_key,
            category=category,
            message=message,
            user=user,
            )

    @staticmethod
    def fromAuthFailure(context, message, user='', cookie='', eas=True):
        category = "authentication"
        if eas:
            event = AuditEvent.eventFactory(context, category, message=message, user=user, user_cookie=cookie)
            event.ip_src = context.user.host
            event.port_src = context.user.port
        else:
            source_key = "Audit"
            event = AuditEvent(
                        source_key,
                        category=category,
                        message=message
                    )
        return event

    def __init__(
            self,
            source_key,
            category='',
            message='',
            uniqueid=None,
            ip_src=None,
            ip_dst=None,
            port_src = None,
            port_dst = None,
            user='',
            timestamp=None,
            used=False,
            ):

        Entity.__init__(self)
        BaseAuditEvent.__init__(
            self, category, PRIORITY_EVENT, message
            )

        if ip_src is None:
            self.ip_src = ''
        else:
            self.ip_src = ip_src
        if ip_dst is None:
            self.ip_dst = ''
        else:
            self.ip_dst = ip_dst
        if port_src is None:
            self.port_src = 0
        else:
            self.port_src = port_src
        if port_dst is None:
            self.port_dst = 0
        else:
            self.port_dst = port_dst

        if timestamp is None:
             timestamp = datetime.now()
        self.timestamp = timestamp

        self.user = unicode(user)
        self.uniqueid = uniqueid
        self.category = unicode(category)
        self.used = False
        self.source_key = unicode(source_key)
        self.message = unicode(message)
        self.weight = WEIGHT[category]

    def _text(self):
        return u"%s: id=%s %s" % (
            self.source_key, self.uniqueid, self.message
            )

    text = property(fget=_text)

    def _source(self):
        return "%s" % self.source_key

    source = property(fget=_source)

    def _toTimestamp(self, time):
        if isinstance(time, datetime):
            return int(mktime(time.timetuple()))

    def exportXMLRPC(self):
        serialized = BaseAuditEvent.exportXMLRPC(self)
        serialized['message'] = "%s" % check_value(self.message)
        serialized['timestamp'] = self._toTimestamp(check_value(self.timestamp)),
        serialized['user'] = unicode(check_value(self.user)),
        serialized['ip_info'] = "source: %s:%s" % (check_value(self.ip_src), check_value(self.port_src))
        return serialized

    @staticmethod
    def get_all():
        return AuditEvent.query.all()

    def __repr__(self):
        return "<%s category=%s text=%r>" \
            % (self.__class__.__name__, self.category, self.text)

    def __unicode__(self):
        return self.text

_MAIL_TEMPLATE = """\
Message: %s

Events triggering this alert:
%s
"""

class CorrelatorAlert(BaseAuditEvent, Entity):

    uniqueid = Field(Integer, primary_key=True)
    message = Field(UnicodeText)
    category = Field(Unicode(50))
    acknowledged = Field(Boolean)
    ack_user = Field(Unicode(100))
    ack_timestamp = Field(TIMESTAMP(100))
    ack_message = Field(UnicodeText)
    creation_timestamp = Field(TIMESTAMP(100))
    priority = Field(Integer)

    events = OneToMany('AuditEvent')
    using_options(tablename="alert", session=connector.session, metadata=connector.metadata)

    attrs = "message category acknowledged ack_user ack_message".split()

    def __init__(
            self,
            events,
            message,
            category='',
            acknowledged=False,
            ack_user='',
            ack_timestamp=None,
            ack_message='',
            creation_timestamp=None
            ):

        if not isinstance(events, (tuple, list, set)):
            events = list(events)

        if any(not isinstance(event, AuditEvent) for event in events):
            raise TypeError("Expected events as %s, but got %s" % (AuditEvent, repr([event.__class__ for event in events])))

        if ack_timestamp is None:
            ack_timestamp = datetime.now()

        if creation_timestamp is None:
            creation_timestamp = datetime.now()

        theoretical_len = len(events)
        real_len = len(frozenset(events))

        if theoretical_len != real_len:
            raise ValueError("Some events are not unique: you pretend to give me %s events, but they are only %s. ids: %s" % (theoretical_len, real_len, [id(event) for event in events]))

#        if any(event.used for event in events):
#            raise ValueError("At least one event already belong to an alert")

        for event in events:
            event.used = True

        Entity.__init__(self)
        BaseAuditEvent.__init__(self, events[0].category,
            PRIORITY_ALERT, message)

        self.events = events
        self.message = unicode(message)
        self.category = unicode(category)
        self.acknowledged = acknowledged
        self.ack_user = unicode(ack_user)
        self.ack_timestamp = ack_timestamp
        self.ack_message = unicode(ack_message)
        self.creation_timestamp = creation_timestamp

        status = 'ACK' if self.acknowledged else 'PENDING'
        self.text = u"[%s]%s: %s" % (status, self.category, self.message)

        assert isinstance(self.acknowledged, bool)

    def toMail(self):
        subject = "[EdenWall Alert %s]" % self.category
        body = _MAIL_TEMPLATE % (
            self.message,
            "\n\n".join(event.text for event in self.events)
            )

        return subject, body

    def acknowledge(self, user, message):
        """ Acknowledges an alert """
        if len(message) == 0:
            message = "Default acknowledged message"
        if self.acknowledged:
            raise CoreError(ALERT_ALREADY_ACK, "acknowledgement done already")
        self.acknowledged = True
        self.ack_timestamp = datetime.now()
        self.ack_message = unicode(message)
        self.ack_user = unicode(user)

    def exportXMLRPC(self):
        xmlrpc = BaseAuditEvent.exportXMLRPC(self)
        xmlrpc['events'] = [event.exportXMLRPC() for event in self.events]
        xmlrpc['timestamp'] = int(mktime(check_value(self.ack_timestamp.timetuple())))
        xmlrpc['acknowledged'] = check_value(self.acknowledged)
        xmlrpc['uniqueid'] = check_value(self.uniqueid)
        xmlrpc['category'] = check_value(self.category)
        return xmlrpc

    def __eq__(self, other):
        if len(self.events) != len(other.events):
            return False

        if self.acknowledged != other.acknowledged:
            return False

        for event in self.events:
            if any(otherevent == event for otherevent in other.events):
                continue
            else:
                return False
        return BaseAuditEvent.__eq__(self, other)

    @staticmethod
    def get_all():
        return CorrelatorAlert.query.all()

    @staticmethod
    def get_last(nb):
        return CorrelatorAlert.query.all()

    def __repr__(self):
        return "<%s id=%s category=%s text=%r>" \
            % (self.__class__.__name__, self.uniqueid, self.category, self.message)

    def __unicode__(self):
        return "[%s] %s" % (self.category, self.message)

_CONFIG_TEMPLATE = """
[alert_creation_threshold]
source = %s
category = %s
[correlator]
events_in_memory = %s
time_combination = %s
threshold_combination = %s
additional_action_enabled = %s
"""
_THRESHOLD_BY_SOURCE = 5
_THRESHOLD_BY_CATEGORY = 3
_EVENTS_IN_MEMORY = 10
_COMBINATION_TIME = 3600 # seconds
_COMBINATION_THRESHOLD = 500
class Audit(Component):
    """
    Manager audit events. Use emit(AuditEvent(...)) to emit an event.

    Audit has a correlator to detect multiple events from the same source or category.
    """
    NAME = "audit"
    API_VERSION = 2
    VERSION = "1.0"
    #ROLES = {
    #    'audit_read': frozenset((
    #        "getEvents",
    #        "getAlerts",
    #        "ackAlerts",
    #        "parameters",
    #        "getAlertsByDate",
    #        "getVersion",
    #    )),
    #    'audit_config': frozenset((
    #        "configure",
    #    ))
    #}

    ACLS = {
        'contact': frozenset(('sendMailToAdmin',)),
        }

    def init(self, core):
        #Base attributes
        self.core = core
        self.events = deque()
        self.by_source = defaultdict(deque)
        self.by_category = defaultdict(deque)
        self.by_combination = {}
        self.audit_conf_file = join(
            core.config.get("CORE", "vardir"),
            AUDIT_CONF_FILE
            )

        #Initialization
        #self._read_thresholds()

        # Set core attribute
        core.audit = self
        #try:
        #    self.read_objects()
        #except Exception, err:
        #    message =  u'Connection error. Database seem to be disconnected. \nComponent will be available one database will be connected'
        #    connector.rollback()
        #    self.critical(message)

    def _getint_or_default(self, config, section, option, default):
        if config.has_option(section, option):
            return config.getint(section, option)
        return default

    def _getbool_or_default(self, config, section, option, default):
        if config.has_option(section, option):
            return config.getboolean(section, option)
        return default


    def _read_thresholds(self):
        config = SafeConfigParser()
        config.read(self.audit_conf_file)
        self.source_threshold = self._getint_or_default(
            config, "alert_creation_threshold", "source", _THRESHOLD_BY_SOURCE
            )
        self.category_threshold = self._getint_or_default(
            config, "alert_creation_threshold", "category", _THRESHOLD_BY_CATEGORY
            )
        self.max_stored_events = self._getint_or_default(
            config, "correlator", "events_in_memory", _EVENTS_IN_MEMORY
            )
        self.additional_action_enabled = self._getbool_or_default(
            config, "correlator", "additional_action_enabled", False
            )
        self.combination_time = self._getint_or_default(
            config, "correlator", "time_combination", _COMBINATION_TIME
            )
        self.combination_threshold = self._getint_or_default(
            config, "correlator", "threshold_combination", _COMBINATION_THRESHOLD
            )

    def _write_thresholds(self):
        with open(self.audit_conf_file, 'w') as fd:
            fd.write(_CONFIG_TEMPLATE % (
                self.source_threshold,
                self.category_threshold,
                self.max_stored_events,
                self.combination_time,
                self.combination_threshold,
                int(self.additional_action_enabled) #bool as integer
                ))

    def _addevent(self, event):
        #keep event list small
        if len(self.events) >= self.max_stored_events:
            self.popleft()
        self.by_source[event.source_key].append(event)
        self.by_category[event.category].append(event)
        self.by_combination[event.timestamp] = event
        self.events.append(event)

    def popleft(self):
        if self.events:
            removed = self.events.popleft()
        self._forgetevent(removed)

    def _forgetevent(self, event):
        try:
            self.events.remove(event)
        except ValueError:
            pass
        try:
            self.by_source[event.source_key].remove(event)
        except ValueError:
            pass
        try:
            self.by_category[event.category].remove(event)
        except ValueError:
            pass

    def read_objects(self):

        #The following generates:
        #   SELECT event.uniqueid AS event_uniqueid, [...]
        #   FROM event
        #   WHERE event.used = %(used_1)s ORDER BY event.timestamp DESC
        self.events.clear()
        for event in AuditEvent.query.filter_by(used=False)[:self.max_stored_events]:
            self._addevent(event)
        self.info("Restored %s events from database." % len(self.events))
        connector.commit()

    def _correlator(self, event):
        if isinstance(event, CorrelatorAlert):
            # Ignore correlator events
            return None

        source_key = event.source_key
        self.check_combination()

        # Source counter
        counter = len(self.by_source[source_key])
        if self.source_threshold <= counter:
            events = self.popsource(source_key)
            self.popcategory(event.category)
            self.popcombination(events)
            return CorrelatorAlert(events,
               u"Correlator: %s events from the same source (%s)" \
               % (counter, event.source_key))

        # Category counter
        counter = len(self.by_category[event.category])
        if self.category_threshold <= counter:
            events = self.popcategory(event.category)
            self.popsource(source_key)
            self.popcombination(events)
            return CorrelatorAlert(events,
                u"Correlator: %s events of the same category (%s)" \
                % (counter, event.category))

        # Combination counter
        counter = 0
        for ev in self.by_combination.values():
            counter += ev.weight
        events = self.by_combination.values()
        if self.combination_threshold <= counter:
            self.popsource(source_key)
            self.popcategory(event.category)
            self.by_combination.clear()
            return CorrelatorAlert(events,
                    u"Correlator: total weight of events has exceed threshold (%s / %s)" \
                    % (counter, self.combination_threshold))

        # No correlation
        return None

    def check_combination(self):
        for time in self.by_combination.keys():
            timestamp_now = timegm(gmtime())
            if self.combination_time < timestamp_now - int(mktime(time.timetuple())):
                self.by_combination.pop(time)

    def popcombination(self, events):
        for event in events:
            if event in self.by_combination.values():
                for key, value in self.by_combination.items():
                    if value == event:
                        self.by_combination.pop(key)

    def popsource(self, source_key):
        events = self.by_source.pop(source_key)
        for event in events:
            self._forgetevent(event)
        return events

    def popcategory(self, category):
        events = self.by_category.pop(category)
        for event in events:
            self._forgetevent(event)
        return events

    def _popleft(self, events, event):
        if not events:
            # empty list
            return
        if events[0] is event:
            events.popleft()

    def emit(self, event):
        return
        # Log the event
        if isinstance(event, CorrelatorAlert):
            # alert
            self.critical(unicode(event))
            for sub_event in event.events:
                self.warning("|-> %s" % unicode(sub_event))

            if self.additional_action_enabled:
                context = Context.fromComponent(self)
                self.core.callService(context, 'contact', 'sendMailToAdmin',
                    *event.toMail()
                    )
            return
        else:
            # event
            self.error(unicode(event))

        self.run_correlator(event)
        if not self.commit():
            self.info("Error: commit failed")

    def commit(self):
        try:
            connector.commit()
            return True
        except Exception, err:
            connector.rollback()
            return False

    def run_correlator(self, event):
        """
        Run the correlator
        """

        # Save the event to the event list
        self._addevent(event)
        correlator_event = self._correlator(event)

        if correlator_event:
            self.emit(correlator_event)

    def service_getEvents(self, context, client_version, alert_id):
        self.check_version(client_version)

        alert = CorrelatorAlert.query.filter_by(uniqueid=alert_id).all()[0]
        results = [event.exportXMLRPC() for event in alert.events]
        if results is None:
            results = []
        return results

    def getAlerts(self, acknowledged):
        #The following generates:
        #   SELECT alert.uniqueid AS alert_uniqueid, [...]
        #   FROM alert
        #   WHERE alert.acknowledged = %(acknowledged_1)s
        return CorrelatorAlert.query.filter_by(acknowledged=acknowledged).all()

    def _connection_error(self):
        message = u'Connection error. Database seem to be disconnected. \nComponent will be available one database will be connected'
        connector.rollback()
        raise CoreError(
            DB_NO_CONNECTION,
            message
            )

    def service_getAlerts(self, context, client_version, ack=False):
        self.check_version(client_version)

        try:
            alerts = self.getAlerts(ack)
        except Exception, err:
            self._connection_error()

        results = [alert.exportXMLRPC() for alert in alerts]
        return results

    def service_ackAlerts(self, context, client_version, alerts_id, message):
        self.check_version(client_version)

        if not context.isUserContext():
            raise CoreError(ACK_FORBIDDEN, "users can ack")
        for id in alerts_id:
            try:
                alert = CorrelatorAlert.get_by(uniqueid=id)
                alert.acknowledge(context.user, message)
                log = ("""Alert %s has been acknowledged :
                          %s """ % (id, AuditEvent.contextinfo(context))
                      )
                self.info(log)
            except Exception, err:
                self._connection_error()
        connector.session.commit()

    def check_version(self, client_version):
        try:
            c_version = float(client_version)
        except TypeError, err:
            raise CoreError("Client version type is unkown")

        if (c_version > float(Audit.VERSION)):
            message = 'Server is older than EAS. You have to upgrade your server'
            raise CoreError(
                API_PROBLEM,
                message
                )

    def getAlertsByDate(self, day, month, year):
        if not all(isinstance(item, int) for item in (day, month, year)):
            raise TypeError("Please supply day, month and year as int")
        base_date = datetime(year, month, day)
        end_of_day = base_date + ONE_DAY
        try:
            query = CorrelatorAlert.query.filter(CorrelatorAlert.creation_timestamp > base_date)
            return query.filter(CorrelatorAlert.creation_timestamp < end_of_day).all()
        except Exception, err:
            self._connection_error()

    def service_getAlertsByDate(self, context, client_version, day, month, year):
        """
        Ignoring version of parameters because we are version 1
        """
        self.check_version(client_version)

        alerts = self.getAlertsByDate(day, month, year)
        results = [alert.exportXMLRPC() for alert in alerts]
        return results

    def service_parameters(self, context, client_version):
        """
        Ignoring version of parameters because we are version 1
        """
        self.check_version(client_version)

        return {
            'source_threshold': self.source_threshold,
            'category_threshold': self.category_threshold,
            'max_stored_events': self.max_stored_events,
            'additional_action_enabled': self.additional_action_enabled,
            'client_version': Audit.VERSION,
            'combination_time' : self.combination_time,
            'combination_threshold' : self.combination_threshold,
            }

    def _check_integer(self, parameters_dict, parameter_name, minimum=0, maximum=None):
        """
        Helper method for the 'configure' service
        By default, if the supplied param is not an int or < 1, we explode
        'minimum', 'maximum' keywords exist
        """
        value = parameters_dict.get(parameter_name, getattr(self, parameter_name))
        if not isinstance(value, int) or value < minimum:
            raise CoreError(
                API_PROBLEM,
                """\
parameters format misanderstanding: '%s' is not an integer > %s (got '%s')\
                """ % (parameter_name, minimum, unicode(value))
                )
        if maximum is not None and value > maximum:
            raise CoreError(
                API_PROBLEM,
                """\
parameters format misanderstanding: '%s' is not an integer <= %s (got '%s')\
                """ % (parameter_name, maximum, unicode(value))
                )

        return value

    def service_configure(self, context, parameters):
        """
        Accepted format:

        {
            'source_threshold': int > 1,
            'category_threshold': int > 1,
            'max_stored_events': 10 <= int <= 1 000 000,
            'client_version': 1,
            'additional_action_enabled': boolean (send e mail)
            'combination_time' : combination_time, : length of time to keep diffeerents kind of events in correlator
            'combination_threshold' : combination_threshold, : threshold to get over to trigger an alert
        }

        supported API version = 1
        """
        if not isinstance(parameters, dict):
            raise CoreError(
                API_PROBLEM,
                "API mismatch between client and server, or wrong usage"
                )
        if 'client_version' in parameters:
            self.check_version(parameters['client_version'])
        else:
            raise CoreError("Client version does not exist.")

        source_threshold = self._check_integer(parameters, 'source_threshold')
        category_threshold = self._check_integer(parameters, 'category_threshold')
        max_stored_events = self._check_integer(parameters, 'max_stored_events', minimum=9, maximum=1000000)
        additional_action_enabled = self._check_integer(parameters, 'additional_action_enabled', minimum=0, maximum=1)
        combination_time = self._check_integer(parameters, 'combination_time')
        combination_threshold = self._check_integer(parameters, 'combination_threshold')

        self.source_threshold = source_threshold
        self.category_threshold = category_threshold
        self.max_stored_events = max_stored_events
        self.additional_action_enabled = bool(additional_action_enabled)
        self.combination_time = combination_time
        self.combination_threshold = combination_threshold
        self._write_thresholds()

        # UserContext
        try:
            message = "Audit configuration has been changed : "
            event = AuditEvent.fromAuditConfModification(context, message)
            self.emit(event)
        except Exception, err:
            self._connection_error()

    def service_getVersion(self, context):
        return Audit.VERSION

connector.setup()

