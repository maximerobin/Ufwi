from .common import setup_connector
connector = setup_connector()
from nucentral.core.audit import AuditEvent, CorrelatorAlert

from .data_gen import mk_dataset

def cmp_id(item_a, item_b):
    return cmp(item_a.uniqueid, item_b.uniqueid)

class TestPersistence(object):

    def test_persistence_equality(self):
        print "test_persistence_equality"
        events, alerts = mk_dataset()

#        event_test = AuditEvent(u"source_", u"source_message", u"misc", u"message")
        connector.session.commit()

        for index, item in enumerate(alerts):
            alerts[index] = connector.session.merge(item)
        for index, item in enumerate(events):
            events[index] = connector.session.merge(item)

        for dataset in (events, alerts):
            dataset.sort(cmp_id)

        first_alert = alerts[0].uniqueid
        first_event = events[0].uniqueid

        alerts2 = CorrelatorAlert.query.filter(CorrelatorAlert.uniqueid >= first_alert).all()
        assert all(isinstance(alert, CorrelatorAlert) for alert in alerts2)
        assert len(alerts) == len(alerts2), "%s !=%s | first-last: %s-%s but got %s-%s" % (len(alerts), len(alerts2), first_alert, alerts[-1].uniqueid, alerts2[0].uniqueid, alerts2[-1].uniqueid)
        events2 = AuditEvent.query.filter(AuditEvent.uniqueid >= first_event).all()
        assert all(isinstance(event, AuditEvent) for event in events2)
        assert len(events) == len(events2)

        for dataset in (events2, alerts2):
            dataset.sort(cmp_id)

        assert events == events2
        assert alerts == alerts2

