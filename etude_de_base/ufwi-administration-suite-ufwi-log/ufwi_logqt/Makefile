PYLUPDATE = pylupdate4
LRELEASE = lrelease-qt4
SOURCES = $(wildcard ../ufwi_log/client/qt/*.py ../ufwi_log/client/qt/*/*.py) $(wildcard ../ufwi_log/core/*.py)
FORMS = $(wildcard ../ufwi_log/client/qt/ui/*.ui)
I18N = $(SOURCES) $(FORMS)
TS_FILES=ufwi_log.fr.ts
QM=$(TS_FILES:%.ts=%.qm)
RCC = rcc

LANG = fr
# to create a translation file:
# pylupdate4 *.ui -ts console_edenwall_${lang}.ts
# and update LANG

all: ufwi_log.rcc $(TS) $(QM)

%.qm: %.ts
	$(LRELEASE) $^

$(TS_FILES): lupdate

ufwi_log.rcc: ufwi_log.qrc $(QM)
	$(RCC) -o $@ -binary $<


lupdate: $(SOURCES) $(FORMS)
	@echo "Update $@"
	@echo "SOURCES = $(SOURCES)" > ufwi_log.pro; \
	echo "FORMS = $(FORMS)" >> ufwi_log.pro; \
	echo "TRANSLATIONS = $(TS_FILES)" >> ufwi_log.pro; \
	$(PYLUPDATE) ufwi_log.pro

clean:
	rm -f ufwi_log.rcc
	rm -f $(QM) ufwi_log.pro
