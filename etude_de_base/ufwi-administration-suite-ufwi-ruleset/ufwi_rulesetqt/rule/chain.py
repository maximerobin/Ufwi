"""
Copyright (C) 2009-2011 EdenWall Technologies

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

from PyQt4.QtCore import Qt
from PyQt4.QtGui import QTableWidgetItem, QColor

from ufwi_rpcd.common import tr
from ufwi_rpcd.common.tools import abstractmethod
from ufwi_rpcc_qt.tools import unsetFlag

from ufwi_rulesetqt.rule.decision_dialog import DecisionDialog

DECISION_COLORS = {
    'ACCEPT': QColor(122, 180, 29),
    'DROP': QColor(234, 117, 44),
    'REJECT': QColor(248, 233, 48),
}

class NatChain(list):
    def __init__(self, rules=None):
        if rules:
            list.__init__(self, rules)
        else:
            list.__init__(self)

    def __repr__(self):
        return "<%s>" % self.__class__.__name__

    @abstractmethod
    def __unicode__(self):
        pass

    def _setTableWidgetItemAttr(self, item):
        item.setText(unicode(self))
        item.setBackgroundColor(DECISION_COLORS['ACCEPT'])

    def createTableWidgetItem(self):
        item = QTableWidgetItem()
        unsetFlag(item, Qt.ItemIsEditable)
        item.setTextAlignment(Qt.AlignHCenter)
        self._setTableWidgetItemAttr(item)
        return item

    def editDefaultDecision(self, window, controler):
        # NAT chains are not editable
        pass

    def getFirstEditableOrder(self):
        for order, rule in enumerate(self):
            if rule['editable']:
                return order
        return None

class PreRoutingChain(NatChain):
    def __unicode__(self):
        return tr("Destination NAT")

class PostRoutingChain(NatChain):
    def __unicode__(self):
        return tr("Source NAT")

class FilterChain(NatChain):
    def __init__(self, model, key, rules=None):
        NatChain.__init__(self, rules)
        self.default_decisions = model.default_decisions
        self.key = key

    def editDefaultDecision(self, window, controler):
        dialog = DecisionDialog(window, controler, self)
        dialog.execLoop()

    def _setTableWidgetItemAttr(self, item):
        decision, use_log = self.default_decisions.get(self.key)
        log = tr("log") if use_log else tr("no log")
        text = u"<%s> (default: %s, %s)" % (unicode(self), decision, log)
        item.setText(text)
        item.setBackgroundColor(DECISION_COLORS[decision])

class InputChain(FilterChain):
    def __init__(self, model, rules=None):
        FilterChain.__init__(self, model, "INPUT", rules)

    def __unicode__(self):
        return u"INPUT"

class OutputChain(FilterChain):
    def __init__(self, model, rules=None):
        FilterChain.__init__(self, model, "OUTPUT", rules)

    def __unicode__(self):
        return u"OUTPUT"

class ForwardChain(FilterChain):
    def __init__(self, model, input, output, acls=None):
        FilterChain.__init__(self, model, (input, output), acls)
        self.right_arrow_character = model.window.right_arrow_character
        self.input = input     # interface identifier (unicode)
        self.output = output   # interface identifier (unicode)

    def __unicode__(self):
        return self.input + self.right_arrow_character + self.output

    def __repr__(self):
        return "<%s %s=>%s>" % (self.__class__.__name__, self.input, self.output)

