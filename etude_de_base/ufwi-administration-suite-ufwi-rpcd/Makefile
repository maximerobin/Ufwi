NUCENTRALDIR=/var/lib/ufwi-rpcd
SHAREDIR=/usr/share/ufwi-rpcd
ETCDIR=/etc/ufwi-rpcd
USER=root
GROUP=root

INSTALL=install -o $(USER) -g $(GROUP)
INSTALLDIR=$(INSTALL) -m 0775 -d
PYLUPDATE = pylupdate4
LRELEASE = lrelease
PYTHON = python

SOURCES = $(wildcard ufwi_rpcd/core/*.py)
SOURCES += $(wildcard ufwi_rpcd/core/auth/*.py)
SOURCES += $(wildcard ufwi_rpcd/core/config/*.py)
SOURCES += $(wildcard ufwi_rpcd/client/*.py)
SOURCES += $(wildcard ufwi_rpcd/common/*.py)
SOURCES += $(wildcard ufwi_rpcd/backend/*.py)
I18N = $(SOURCES) $(FORMS)
TS=ufwi-rpcd.fr.ts
QM=ufwi-rpcd.fr.qm

.PHONY: clean

all: $(QM)

ufwi-rpcd.pro:
	@echo "Create $@"
	@echo "SOURCES = $(SOURCES)" > ufwi-rpcd.pro; \
	echo "FORMS = $(FORMS)" >> ufwi-rpcd.pro; \
	echo "TRANSLATIONS = $(TS)" >> ufwi-rpcd.pro

$(TS): ufwi-rpcd.pro $(SOURCES) $(FORMS)
	$(PYLUPDATE) ufwi-rpcd.pro

$(QM): $(TS)
	$(LRELEASE) ufwi-rpcd.pro

install: installdirs install_qm install_python install_conf
	$(INSTALL) tools/ufwi_rpcd_client /usr/bin/
	$(INSTALL) ufwi-rpcd.tac /usr/sbin/

install_python:
	$(PYTHON) setup.py install

install_qm: $(QM)
	$(INSTALL) $(QM) $(SHAREDIR)/i18n

installdirs:
	$(INSTALLDIR) $(NUCENTRALDIR)
	$(INSTALL) -m 0700 -d $(NUCENTRALDIR)/sessions
	$(INSTALLDIR) $(NUCENTRALDIR)/locks
	$(INSTALLDIR) $(NUCENTRALDIR)/files
	$(INSTALLDIR) $(NUCENTRALDIR)/files-users
	$(INSTALLDIR) $(NUCENTRALDIR)/user_configurations
	$(INSTALLDIR) $(NUCENTRALDIR)/mods-enabled
	$(INSTALLDIR) $(NUCENTRALDIR)/versionned
	$(INSTALLDIR) $(NUCENTRALDIR)/repositories
	$(INSTALLDIR) $(SHAREDIR)
	$(INSTALLDIR) $(SHAREDIR)/resources
	$(INSTALLDIR) $(SHAREDIR)/i18n
	$(INSTALLDIR) $(SHAREDIR)/templates
	$(INSTALLDIR) $(ETCDIR)
	$(INSTALLDIR) /var/cache/ufwi-rpcd

install_conf:
	test -e $(ETCDIR)/default.ufwi-rpcd.conf \
	|| $(INSTALL) default.ufwi-rpcd.conf $(ETCDIR)
	test -e $(NUCENTRALDIR)/users \
	|| echo "admin:{PLAIN}admin" > $(NUCENTRALDIR)/users
	test -e $(NUCENTRALDIR)/groups \
	|| echo "admin:admin" > $(NUCENTRALDIR)/groups
	test -e $(NUCENTRALDIR)/acl.db \
	|| sqlite3 $(NUCENTRALDIR)/acl.db < doc/sql/acl_sqlite_debug.sql

clean:
	rm -f ufwi-rpcd.pro $(QM)

