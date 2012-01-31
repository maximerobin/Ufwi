#!/usr/bin/python
import psycopg2
from random import choice
import time

CATEGORIES = ("authentication", "service", "spoof", "misc")
ACK_USER = ("Pierre", "Eric", "Francois", "Laurent", "Loic")

class DataBaseManager(object):

    def __init__(self):
        self.conn = None
        self.cur = None

    def connect(self):
        conf = {
                'database' : 'edenaudit',
                'hostname' : 'localhost',
                'username' : 'edenaudit',
                'password' : '1234',
               }
        try:
            self.conn = psycopg2.connect(database=conf['database'], host=conf['hostname'], user=conf['username'], password=conf['password'])
            self.cur = self.conn.cursor()
            return True
        except:
            print "I am unable to connect the database"
            return False

    def execute(self, query):
        try:
            self.cur.execute(query)
            if "INSERT" in query:
                return
            if self.cur.rowcount > 0:
                return self.cur.fetchall()
            else:
                return []

        except Exception, err:
            #print "You are not connected to the database"
            print err

    def commit(self):
        self.conn.commit()

    def disconnect(self):
        self.cur.close()
        self.conn.close()


db = DataBaseManager()
db.connect()

# ************* Create alerts **************
nb_alerts = 50
alerts = []
for index in xrange(nb_alerts):
    message = "Message alert " + str(index)
    category = CATEGORIES[index % len(CATEGORIES)]
    acknowledged = True if (index % 3) == 0 else False
    ack_user = ACK_USER[index % len(ACK_USER)]
    timestamp = time.time() + 3200 * index
    ack_message = "message ack " + str(index) if index % 4 == 0 else ""

    alerts.append(
                  {
                   'message' : message,
                   'category' : category,
                   'acknowledged' : acknowledged,
                   'ack_user' : ack_user,
                   'timestamp' : timestamp,
                   'ack_message' : ack_message
                  }
                 )
    query = """INSERT INTO alert (message, category, acknowledged, ack_user, ack_timestamp, ack_message) VALUES ('%s', '%s', '%s', '%s', to_timestamp('%s'), '%s')""" % (message, category, str(acknowledged), ack_user, timestamp, ack_message)

    db.execute(query)
db.commit()
# ************* Create events **************
nb_events = 400
events = []

query = """SELECT uniqueid, category FROM alert"""
alerts = db.execute(query)

if alerts is None:
    print "No alerts. Problem"
    exit()

for index in xrange(nb_events):
    alert_uniqueid =  alerts[index % len(alerts)][0]
    message = "Message event " + str(index)
    #category = alerts[index % nb_alerts]['category']
    category = alerts[index % len(alerts)][1]
    ip_src = "192.168.1." + str((index + 1) % 255)
    ip_dst = "10.0.2." + str((index + 1) % 255)
    port_src = choice(xrange(80, 10000, 1))
    port_dst = choice(xrange(80, 10000, 1))
    priority = choice(xrange(1, 10, 1))
    source_message = "Source message " + str(index)

    query = """INSERT INTO event (alert_uniqueid, message, category, ip_src, ip_dst, port_src, port_dst, priority, source_message) VALUES (%d, '%s', '%s', ('%s')::inet, ('%s')::inet, %d, %d, %d, '%s')""" % (alert_uniqueid, message, category, ip_src, ip_dst, port_src, port_dst, priority, source_message)

    db.execute(query)

db.commit()
db.disconnect()



