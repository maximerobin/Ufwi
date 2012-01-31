#!/usr/bin/python
"""
This is a special test file:
Here I mimic py.test behaviour to be able to run the test manually with
% python test_component.py...
and see the backtrace when I hit ^C
"""

ismain = __name__ == '__main__'

if ismain:
    from common import setup_connector
    setup_connector = setup_connector
else:
    from .common import setup_connector
connector = setup_connector()
from os.path import exists
from tempfile import mkdtemp
import py.test

from nucentral.backend.error import CoreError
from nucentral.core.mockup import Core

from nucentral.core.mockup import Context
from nucentral.core.audit import Audit

if ismain:
    from data_gen import mk_dataset, mk_events_set
    mk_dataset, mk_events_set = mk_dataset, mk_events_set
else:
    from .data_gen import mk_dataset, mk_events_set

def _build_component():
    return Audit()

def init_component():
    core = Core()
    temp = mkdtemp()
    core.config.set("CORE", "vardir", temp)
    component = _build_component()
    component.init(core)
    return component

def _test_write_conf(parameters, expect_ok):
    audit = init_component()
    context = Context.make_component()
    if not expect_ok:
        py.test.raises(CoreError, "audit.service_configure(context, parameters)")
        return

    print "parameters", parameters
    audit.service_configure(context, parameters)
    assert exists(audit.audit_conf_file)

def _test_read_conf():
    audit = init_component()
    context = None
    api = 1
    parameters = audit.service_parameters(context, api)
    assert all(isinstance(value, int) for value in parameters.values())

def test_gen():
    yield _build_component
    yield init_component
    #inject a lot of things in db
    mk_dataset()
    mk_dataset()
    yield _build_component
    yield init_component

    standard_params = {
        'source_threshold': 2,
        'category_threshold': 2,
        'max_stored_events': 10,
        'api_version': 1
    }
    yield _test_write_conf, standard_params, True
    nok_params = {
        'source_threshold': -1,
        'category_threshold': 2,
        'max_stored_events': 10,
        'api_version': 1
    }
    yield _test_write_conf, nok_params, False
    nok_params = {
        'source_threshold': 2,
        'category_threshold': -1,
        'max_stored_events': 10,
        'api_version': 1
    }
    yield _test_write_conf, nok_params, False
    nok_params = {
        'source_threshold': 2,
        'category_threshold': 2,
        'max_stored_events': 10,
        'api_version': 4
    }
    yield _test_write_conf, nok_params, False
    yield _test_read_conf

def test_correlator():
    audit = init_component()
    known_alerts = frozenset(audit.getAlerts(False))
    for event in mk_events_set(100):
        audit.emit(event)
    all_alerts = frozenset(audit.getAlerts(False))
    assert known_alerts.issubset(all_alerts)
    assert len(known_alerts) < len(all_alerts)

def test_bydate():
    audit = init_component()
    context = None
    api_version = 1
    day = 1
    month = 1
    year = 2010
    alerts = audit.service_getAlertsByDate(
        context,
        api_version,
        day,
        month,
        year
        )

if ismain:
    for item in test_gen():
        try:
            func = item[0]
        except TypeError:
            func = item
            func.__call__()
        else:
            print "running test %s" % func.__name__
            if len(item) > 1:
                func(*item[1:])

