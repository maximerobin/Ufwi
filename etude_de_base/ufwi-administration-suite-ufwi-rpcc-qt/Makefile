SUBDIRS = ufwi_rpcc_qt

INSTALL=install -m 0644
PYLUPDATE = pylupdate4
LRELEASE=lrelease

SHAREDIR=/usr/share/ufwi-rpcc-qt

I18N=$(wildcard ufwi_rpcc_qt/*.py) $(wildcard ufwi_rpcc_qt/*.ui)
TS=ufwi-rpcc-qt.fr.ts
QM=$(TS:%.ts=%.qm)
RCC=rcc

RESOURCES=$(shell find resources -type f -print)

all: $(QM) ufwi-rpcc-qt.rcc
	$(MAKE) recursive SUB_TARGET=all

ufwi-rpcc-qt.rcc: resources/ufwi-rpcc-qt.qrc $(RESOURCES)
	$(RCC) -o $@ -binary $<

$(TS): $(I18N)
	@echo "Update $@"
	@$(PYLUPDATE) $(I18N) -ts $@

$(QM): $(TS)
	$(LRELEASE) $<

install: $(QM)
	$(INSTALL) $(QM) $(SHAREDIR)/i18n
	$(INSTALL) ufwi-rpcc-qt.rcc $(SHAREDIR)/resources

clean:
	$(MAKE) recursive SUB_TARGET=clean

recursive:
	for d in $(SUBDIRS); do \
		$(MAKE) -C $$d $(SUB_TARGET); \
	done
