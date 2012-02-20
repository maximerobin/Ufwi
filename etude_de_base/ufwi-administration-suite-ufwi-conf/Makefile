# Translation : only source files are processed

SHELL=bash

# User options
USER=root
GROUP=root
DESTDIR=

# Directories
PREFIX=$(DESTDIR)/usr
STORAGEDIR=$(DESTDIR)/var/lib/ufwi-rpcd/storage
SHAREDIR=$(PREFIX)/share/ufwi-rpcd

# Programs
PYLUPDATE = pylupdate4
LRELEASE=lrelease-qt4
RCC = rcc
LNSYM=ln -sfn
INSTALL=install -o $(USER) -g $(GROUP)
INSTALLDIR=$(INSTALL) -m 0775 -d
INSTALLFILE=$(INSTALL) -m 0664

# Input files
SRCDIR=$(shell pwd -P)
SOURCES = $(shell find . -name "*.py" |xargs)

RESOURCES = ufwi_conf/client/system/system.rcc
QRC = $(RESOURCES:%.rcc=%.qrc)
TS = $(RESOURCES:%.rcc=%.fr.ts)
QM = $(TS:%.ts=%.qm)

.PHONY: clean ufwi_conf_client lrelease update_sources

# first PYLUPDATE process .ui files (see ufwi_conf/client/Makefile)
# next PYLUPDATE process all source
# next LRELEASE
# next RCC
all:
	@echo "commands:"
	@echo " make install: install ufwi_conf backend"
	@echo " make install_qt: install ufwi_conf frontend"

update_sources:
	$(MAKE) -C ufwi_conf/client

lrelease: $(TS)
	$(LRELEASE) $(TS)

$(TS): update_sources $(SOURCES)
	@echo "Update $@"
	@$(PYLUPDATE) $(SOURCES) -ts $@

$(RESOURCES): $(QRC) lrelease
	$(RCC) -o $@ -binary $<

install: installpython

install_qt: $(RESOURCES) installfiles installpython_qt

installdirs:
	$(INSTALLDIR) $(SHAREDIR)/resources
	$(INSTALLDIR) $(SHAREDIR)/data

installfiles: installdirs $(RESOURCES)
	$(INSTALLFILE) $(RESOURCES) $(SHAREDIR)/resources

installpython:
	./setup_ufwi_conf_common.py install --prefix=$(PREFIX)
	./setup_ufwi_conf_backend.py install --prefix=$(PREFIX)

installpython_qt: update_sources
	./setup_ufwi_conf_client.py install --prefix=$(PREFIX)

# Installation for developers
installdev: installdirs ufwi_conf
	$(LNSYM) $(SRCDIR)/$(RESOURCES) $(SHAREDIR)/resources

clean:
	rm -f $(QM) $(RESOURCES)
	$(MAKE) -C ufwi_conf/client clean

help:
	@echo "... lrelease : create qm files"
	@echo "... clean    : clean generated files"
