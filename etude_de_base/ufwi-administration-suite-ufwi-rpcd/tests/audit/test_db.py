from py.test import raises

from .common import setup_connector
connector = setup_connector()
from nucentral.core.audit import AuditEvent, CorrelatorAlert

from .data_gen import mk_dataset


class TestDB(object):

    def purge_data(self):
        for event in AuditEvent.get_all():
            event.delete()

        for alert in CorrelatorAlert.get_all():
            alert.delete()

    def test_save(self):

        events, alerts = mk_dataset()
        connector.commit()

    def test_update(self):
        self.test_save()
        #shortcut to get one alert
        alert = CorrelatorAlert.get_by(acknowledged=False)
        assert not alert.acknowledged
        alert.acknowledge('user1', 'dummy message')
        uniqueid = alert.uniqueid
        connector.commit()

        del alert

        alert = CorrelatorAlert.get_by(uniqueid=uniqueid)
        assert isinstance(alert, CorrelatorAlert)
        assert alert.uniqueid == uniqueid
        assert alert.acknowledged



    def test_cannot_purge(self):
        raises(Exception, 'purge_data()')
        connector.session.rollback()

    def test_gen_loop(self):
        yield self.test_save
        yield self.test_cannot_purge
        yield self.test_save
        yield self.test_cannot_purge

