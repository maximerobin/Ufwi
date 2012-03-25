UI_FILES = $(shell find . -name "*.ui")
UI_PY_FILES = $(UI_FILES:%.ui=%_ui.py)

TS_FILES = multisite.fr.ts
QM_FILES = $(TS_FILES:%.ts=%.qm)

SOURCES = $(shell find . -name "*.py")
I18N = $(SOURCES) $(UI_FILES)

# Programs
PYUIC = pyuic4
PYLUPDATE = pylupdate4
LRELEASE = lrelease
RCC = rcc

all: $(UI_PY_FILES) $(UI_FILES) $(QM_FILES) multisite.rcc

$(TS_FILES): $(I18N)
	@echo "Update $@"
	@$(PYLUPDATE) $(I18N) -ts $@

$(QM_FILES): $(TS_FILES) multisite.pro
	$(LRELEASE) multisite.pro

%_ui.py: %.ui
	$(PYUIC) -o $@ $^
	sed -i '/import multisite_rc/D;/setSortingEnabled/D' $@
	sed -i '/import ufwi_rpcc_qt_rc/D;/setSortingEnabled/D' $@

lrelease: $(QM_FILES)

multisite.pro: lupdate

lupdate: $(UI_FILES)
	@echo "Update $@"
	@echo "SOURCES = $(SOURCES)" > multisite.pro; \
	echo "FORMS = $(UI_FILES)" >> multisite.pro; \
	echo "TRANSLATIONS = $(TS_FILES)" >> multisite.pro; \
	$(PYLUPDATE) multisite.pro

multisite.rcc: multisite.qrc $(QM_FILES)
	$(RCC) -o $@ -binary $<

install:
	$(MAKE) -C qt install

clean:
	rm -f $(QM_FILES)
	rm -f $(UI_PY_FILES) multisite.rcc *.pyc multisite.pro
	$(MAKE) -C qt clean

.PHONY: all clean lupdate lrelease

