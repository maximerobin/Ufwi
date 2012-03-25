# Translation : only .ui files are processed
#
TRANSLATIONS = system/system.fr.ts

SHAREDIR=/usr/share/nucentral
UI_FILES = $(shell find . -name "*.ui" |xargs)
UI_PY_FILES = $(UI_FILES:%.ui=%_ui.py)
PY_FILES = $(shell find . -name "*.py"|grep -v "_ui.py")

TS_FILES = $(shell find . -name "*.ts" |xargs)

PYUIC = pyuic4
PYLUPDATE = pylupdate4

LANG = fr
# to create a translation file:
# lupdate *.ui -ts nucentral_${lang}.ts
# and update LANG

all: $(UI_PY_FILES)

%_ui.py: %.ui
	$(PYUIC) -o $@ $^
	sed -i '/import system_rc/D' $@
	sed -i '/import edenwall_rc/D' $@

%.ts: $(UI_FILES) $(PY_FILES)
	$(PYLUPDATE) $^ -ts $@

clean:
	rm -f $(UI_PY_FILES) *.pyc

help:
	@echo "The following targets are valid for this Makefile:"
	@echo "... all      : compile ui and translation files"
	@echo "... clean    : clean generated files"

.PHONY: all clean lupdate lrelease

