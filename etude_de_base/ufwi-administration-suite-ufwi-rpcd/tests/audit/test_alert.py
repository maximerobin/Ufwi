from py.test import raises
from sys import stderr

from nucentral.backend.error import CoreError
from .common import setup_connector

connector = setup_connector()

from nucentral.core.audit import CorrelatorAlert

from .data_gen import mk_events_set, build_alert, ack_message


class TestAlert(object):

    def test_equality(self):
        #make 10 events
        events_a, events_b, events_c, events_d = (mk_events_set(10) for i in xrange(4))

        #build 2 equal alerts with the 10 events
        alert1 = build_alert(events_a)
        alert2 = build_alert(events_b)

        assert events_a == events_b
        assert alert1 == alert2, "The 2 alerts built with the same 10 events must be equal"
        alert1.acknowledge("testuser", ack_message)
        assert alert1 != alert2, "alert1 is acknowledged while alert2 is not"

        event = mk_events_set(1) #tuple
        alert3 = build_alert(events_c + event)
        assert alert3 != alert1, "There is one more event in alert3 than in alert1"

        alert4 = build_alert(events_d[0:-2])
        assert alert4 != alert1, "There is one more event in alert4 than in alert4"
        assert alert4 != alert2, "There is one more event in alert4 (nack) than in alert2 (ack)"


    def test_build(self):
        events_1 = mk_events_set(3)
        events_2 = mk_events_set(3)
        for events in events_1, events_2:
            alert = build_alert(events)
            assert isinstance(alert, CorrelatorAlert)

#        try:
#            raises(ValueError, "build_alert(events_1 + events_2)")
#            build_alert(events_1 + events_2)
#        except:
#            stderr.write("some events are already used, they cannot be re used to build an alert")
#            raise

    def test_build_different_events(self):
        event = mk_events_set(1)
        print "event", event
        events = event * 10
        try:
            raises(ValueError, "build_alert(events)")
        except:
            stderr.write("Should not build an alert with several times the same event")
            raise

    def _test_ack(self, alert):
        assert not alert.acknowledged
        alert.acknowledge("test_user", ack_message)
        assert alert.acknowledged

    def _test_initial_cond(self, alert):
        alert.acknowledge("test_user0", ack_message)
        raises(CoreError, "alert.acknowledge(\"test_user1\", ack_message)")

    def test_gen_tests(self):
        for method in self._test_ack, self._test_initial_cond:
            alert = build_alert()
            yield(method, alert)


