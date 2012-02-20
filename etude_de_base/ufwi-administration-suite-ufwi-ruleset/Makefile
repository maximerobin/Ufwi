SHELL=bash

# User options
USER=root
GROUP=root
DESTDIR=

# Directories
PREFIX=$(DESTDIR)/usr
NUFACEDIR=$(DESTDIR)/var/lib/ufwi-ruleset
SHAREDIR=$(PREFIX)/share/ufwi-rpcc-qt

# Programs
LNSYM=ln -sfn
INSTALL=install -o $(USER) -g $(GROUP)
INSTALLDIR=$(INSTALL) -m 0775 -d
INSTALLFILE=$(INSTALL) -m 0664

# Input files
SRCDIR=$(shell pwd -P)

.PHONY: clean ufwi_rulesetqt

all:
	@echo "commands:"
	@echo " make install: install ufwi-ruleset backend"
	@echo " make install_qt: install ufwi-ruleset Qt frontend"

ufwi_rulesetqt:
	$(MAKE) -C ufwi_rulesetqt

install: installfiles installpython

install_qt: ufwi_rulesetqt installpython_qt

installdirs:
	$(INSTALLDIR) $(NUFACEDIR)
	$(INSTALLDIR) $(NUFACEDIR)/rulesets
	$(INSTALLDIR) $(NUFACEDIR)/templates
	$(INSTALLDIR) $(NUFACEDIR)/local_rules_ipv4.d
	$(INSTALLDIR) $(NUFACEDIR)/local_rules_ipv6.d
	$(INSTALLDIR) $(SHAREDIR)/resources

installfiles: installdirs ufwi_rulesetqt
	$(INSTALLFILE) example/library.xml $(NUFACEDIR)/library.xml
	$(INSTALLFILE) ufwi_rulesetqt/ufwi-ruleset.rcc $(SHAREDIR)/resources

installpython:
	./setup_ufwi_ruleset.py install --prefix=$(PREFIX)

enmod:
	test -e /var/lib/ufwi-rpcd/mods-enabled/ \
	|| ln -s $(shell cd /; python -c "import ufwi_ruleset.forward, os.path; print os.path.dirname(ufwi_ruleset.forward.__file__)") /var/lib/ufwi-rpcd/mods-enabled/

installpython_qt:
	./setup_ufwi_rulesetqt.py install --prefix=$(PREFIX)

# Installation for developers
installdev: installdirs ufwi_rulesetqt
	$(LNSYM) $(SRCDIR)/example/library.xml $(NUFACEDIR)/library.xml
	$(LNSYM) $(SRCDIR)/example/local_ipv4_firewall.xml $(NUFACEDIR)/templates/
	$(LNSYM) $(SRCDIR)/example/local_ipv6_firewall.xml $(NUFACEDIR)/templates/
	$(LNSYM) $(SRCDIR)/ufwi_rulesetqt/ufwi-ruleset.rcc $(SHAREDIR)/resources

clean:
	$(MAKE) -C ufwi_rulesetqt clean

