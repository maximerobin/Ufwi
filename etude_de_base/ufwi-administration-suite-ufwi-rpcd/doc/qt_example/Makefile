SOURCES = example.py main_window.py services.py
RESOURCES = example.rcc

UI_FILES = main_window.ui
UI_PY_FILES = $(UI_FILES:%.ui=%_ui.py)

TS_FILES = $(shell ls *.ts)
QM_FILES = $(TS_FILES:%.ts=%.qm)

PYUIC = pyuic4
PYLUPDATE = pylupdate4
LRELEASE = lrelease-qt4
RCC = rcc


LANG = fr
# to create a translation file:
# lupdate *.ui -ts nucentral_${lang}.ts
# and update LANG

all: $(UI_PY_FILES) $(QM_FILES) $(RESOURCES)

%_ui.py: %.ui
	$(PYUIC) -o $@ $^

lrelease: $(QM_FILES)

%.qm: %.ts nucentral.pro
	$(LRELEASE) nucentral.pro

nucentral.pro: lupdate

lupdate: $(UI_FILES)
	@echo "Update $@"
	@echo "SOURCES = $(SOURCES)" > nucentral.pro; \
	echo "FORMS = $(UI_FILES)" >> nucentral.pro; \
	echo "TRANSLATIONS = $(TS_FILES)" >> nucentral.pro; \
	$(PYLUPDATE) nucentral.pro

%.rcc: %.qrc $(QM_FILES)
	$(RCC) -o $@ -binary $<

clean:
	rm -f $(UI_PY_FILES) *.pyc *.qm nucentral.pro $(RESOURCES)

help:
	@echo "The following targets are valid for this Makefile:"
	@echo "... all      : compile ui and translation files"
	@echo "... lupdate  : update translation files (edit with 'linguist')"
	@echo "... lrelease : compile translation files"

.PHONY: all clean lupdate lrelease

