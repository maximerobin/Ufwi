from .common import setup_connector
connector = setup_connector()
from data_gen import mk_events_set

class TestEvent:

    def test_events_builder(self):
        mk_events_set(1000)

    def test_events_timestamp(self):
        events = mk_events_set(10)

        for event in events:
            assert isinstance(event.timestamp, int)

    def test_events_equality(self):
        events_1 = mk_events_set(10)
        events_2 = mk_events_set(10)

        assert events_1 == events_2
