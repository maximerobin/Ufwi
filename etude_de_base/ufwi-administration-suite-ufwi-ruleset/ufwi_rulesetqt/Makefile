###########################################################
# Workflow and dependancies:                              #
# ui -> py -> ts -> qm -> qrc -> rcc -> pro               #
# http://doc.trolltech.com/4.4/linguist-manager.html      #
###########################################################

UI_FILES = main_window.ui create_protocol.ui create_resource.ui
UI_FILES += ruleset_dialog.ui rule/iptables_dialog.ui create_user_group.ui
UI_FILES += create_application.ui create_os.ui create_periodicity.ui
UI_FILES += create_duration.ui parameters_dialog.ui nat_wizard.ui
UI_FILES += create_ruleset.ui custom_rules.ui generic_links.ui
UI_FILES += generic_links_copy.ui template_dialog.ui
UI_FILES += default_decision.ui move_rule.ui
UI_PY_FILES = $(UI_FILES:%.ui=%_ui.py)

TS_FILES = ufwi-ruleset.fr.ts
QM_FILES = $(TS_FILES:%.ts=%.qm)

SOURCES = $(shell find .. -name "*.py")
FORMS = $(wildcard *.ui) $(wildcard rule/*.ui)
I18N = $(SOURCES) $(FORMS)

# Programs
PYUIC = pyuic4
PYLUPDATE = pylupdate4
LRELEASE = lrelease
RCC = rcc

all: $(UI_PY_FILES) $(UI_FILES) $(QM_FILES) ufwi-ruleset.rcc

$(TS_FILES): $(I18N)
	@echo "Update $@"
	@$(PYLUPDATE) $(I18N) -ts $@

OLD_LINE=.*self.platform_edit_list.setHeaders.*
NETWORK=QtGui.QApplication.translate(\'MainWindow\', \'Network\', None, QtGui.QApplication.UnicodeUTF8)
PROTOCOL=QtGui.QApplication.translate(\'MainWindow\', \'Protocol\', None, QtGui.QApplication.UnicodeUTF8)
NEW_LINE=self.platform_edit_list.setHeaders([$(NETWORK), $(PROTOCOL)])

main_window_ui.py: main_window.ui
	# Hack (Fixed in pyqt 4.7.1)
	# http://www.mail-archive.com/pyqt@riverbankcomputing.com/msg20586.html
	$(PYUIC) -o $@ $^
	sed -i '/import ufwi-ruleset_rc/D;/setSortingEnabled/D' $@
	sed -i '/import ufwi-rpcc-qt_rc/D;/setSortingEnabled/D' $@
	sed -i "s/$(OLD_LINE)/        $(NEW_LINE)/" $@

%_ui.py: %.ui
	$(PYUIC) -o $@ $^
	sed -i '/import ufwi-ruleset_rc/D;/setSortingEnabled/D' $@
	sed -i '/import ufwi-rpcc-qt_rc/D;/setSortingEnabled/D' $@

%.qm: %.ts
	$(LRELEASE) $< -qm $@

ufwi-ruleset.qrc: $(QM_FILES)

ufwi-ruleset.rcc: ufwi-ruleset.qrc
	$(RCC) -o $@ -binary $<

ufwi-rulesetqt.pro: lupdate ufwi-ruleset.rcc

lupdate: $(UI_FILES)
	@echo "Update $@"
	@echo "SOURCES = $(SOURCES)" > ufwi-rulesetqt.pro; \
	echo "FORMS = $(UI_FILES)" >> ufwi-rulesetqt.pro; \
	echo "TRANSLATIONS = $(TS_FILES)" >> ufwi-rulesetqt.pro; \
	$(PYLUPDATE) ufwi-rulesetqt.pro


clean:
	rm -f $(QM_FILES)
	rm -f $(UI_PY_FILES) ufwi-ruleset.rcc *.pyc ufwi-rulesetqt.pro

.PHONY: all clean lupdate

