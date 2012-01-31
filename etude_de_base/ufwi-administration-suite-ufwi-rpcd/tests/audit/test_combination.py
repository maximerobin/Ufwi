from time import gmtime
from calendar import timegm

ismain = __name__ == '__main__'
if ismain:
    from common import setup_connector
    setup_connector = setup_connector
else:
    from .common import setup_connector
connector = setup_connector()
from .data_gen import mk_events_set
from .test_component import init_component

def test_timeko_weightok():
    audit = init_component()
    event_weight = 20
    audit.combination_threshold = 100
    audit.combination_time = 120
    timestamp_now = timegm(gmtime())

    not_matching_events = \
        mk_events_set(1, timestamp=timestamp_now-42, weight=event_weight)\
        + mk_events_set(1, timestamp=timestamp_now-43, weight=event_weight)\
        + mk_events_set(1, timestamp=timestamp_now-1000, weight=event_weight)

#    assert audit.getAlerts(False) == 0
    for event in not_matching_events:
        audit.emit(event)
    assert len(audit.by_combination) != len(not_matching_events)

def test_timeok_weightok():
    audit = init_component()
    event_weight = 20
    audit.combination_threshold = 100
    audit.combination_time = 120
    timestamp_now = timegm(gmtime())

    matching_events = \
        mk_events_set(1, timestamp=timestamp_now-42, weight=event_weight)\
        + mk_events_set(1, timestamp=timestamp_now-43, weight=event_weight)\
        + mk_events_set(1, timestamp=timestamp_now-44, weight=event_weight)

#    assert audit.getAlerts(False) > 0
    for event in matching_events:
        audit.emit(event)
    assert len(audit.by_combination) == len(matching_events)

def test_timeko_weightko():
    audit = init_component()
    event_weight = 20
    audit.combination_threshold = 100
    audit.combination_time = 120
    timestamp_now = timegm(gmtime())
    audit.by_combination = {}

    not_matching_events = \
        mk_events_set(1, timestamp=timestamp_now-42, weight=event_weight)\
        + mk_events_set(1, timestamp=timestamp_now-43, weight=event_weight)\
        + mk_events_set(1, timestamp=timestamp_now-1000, weight=event_weight)

#    assert audit.getAlerts(False) == 0
    for event in not_matching_events:
        audit.emit(event)
    assert len(audit.by_combination) != len(not_matching_events)

