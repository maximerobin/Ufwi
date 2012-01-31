from nucentral.core.mockup import Context
from nucentral.core.audit import AuditEvent, CorrelatorAlert

from .common import setup_connector

connector = setup_connector()


ack_message = "test acknowledgement"

def build_alert(events=None, number=10):
    if events is None:
        events = mk_events_set(number)
    message = u"message"
    alert = CorrelatorAlert(events, message)
    return alert

def mk_dataset():
    events = mk_events_set(400)
    alerts = []

    for index in xrange(20):
        offset = index*10
        alerts.append(build_alert(
            events[offset:offset+10]
            )
        )

    for offset, user in enumerate(("test_user0", "test_user1")):

        for index in xrange(5*offset, 5+5*offset):
            alerts[index].acknowledge(user, ack_message)
    return events, alerts

def mk_events_set(nb, timestamp=None, weight=20):
    events = []
    context = Context.make_component()
    component = "component_name"
    base_message = "This is a test event"
    for i in xrange(nb):
        event = AuditEvent.fromACL(context, component=component)
        if timestamp:
            event.timestamp = timestamp
        event.weight = weight
        events.append(event)
#        connector.commit()

    return events

