# -*- coding: utf-8 -*-
"""
Copyright (C) 2010-2011 EdenWall Technologies
Written by François Toussenel <ftoussenel AT edenwall.com>

This file is part of NuFirewall. 
 
 NuFirewall is free software: you can redistribute it and/or modify 
 it under the terms of the GNU General Public License as published by 
 the Free Software Foundation, version 3 of the License. 
 
 NuFirewall is distributed in the hope that it will be useful, 
 but WITHOUT ANY WARRANTY; without even the implied warranty of 
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the 
 GNU General Public License for more details. 
 
 You should have received a copy of the GNU General Public License 
 along with NuFirewall.  If not, see <http://www.gnu.org/licenses/>

"""

body_part_new_alerts = {
    "en": "New alerts:",
    "fr": u"Nouvelles alertes :",
    }
body_part_old_alerts = {
    "en": "Old alerts:",
    "fr": u"Anciennes alertes :",
    }
body_part_others = {
    "en": "Other states:",
    "fr": u"Autres états:",
    }

class SupervisorMail:
    def __init__(self, config = None):
        self.clear()
        self.set_config(config)

    def clear(self):
        self.new_alerts = {}
        self.old_alerts = {}
        self.others = {}

    def set_config(self, config):
        self.config = config

    def add(self, kind, name, message):
        if name in kind:
            kind[name].append(message)
        else:
            kind[name] = [message]

    def add_alert(self, name, new, message):
        if new:
            kind = self.new_alerts
        else:
            kind = self.old_alerts
        self.add(kind, name, message)

    def add_other(self, name, message):
        self.add(self.others, name, message)

    def make_body(self):
        body = body_part_new_alerts.get(
            self.config.language,
            body_part_new_alerts["en"]) + "\n\n"
        for group in self.new_alerts.values():
            for message in group:
                body += "%s\n" % message
            body += "\n"

        body += "\n" + body_part_old_alerts.get(
            self.config.language,
            body_part_old_alerts["en"]) + "\n\n"
        for group in self.old_alerts.values():
            for message in group:
                body += "%s\n" % message
            body += "\n"

        body += "\n" + body_part_others.get(
            self.config.language,
            body_part_others["en"]) + "\n\n"
        for group in self.others.values():
            for message in group:
                body += "%s\n" % message
            body += "\n"

        return body
