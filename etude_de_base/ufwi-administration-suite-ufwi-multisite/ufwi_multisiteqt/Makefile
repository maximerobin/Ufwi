SHELL=bash

# Directories
PREFIX=$(DESTDIR)/usr
SHAREDIR=$(PREFIX)/share/nucentral

# Programs
LNSYM=ln -sfn
INSTALL=install -o $(USER) -g $(GROUP)
INSTALLDIR=$(INSTALL) -m 0775 -d
INSTALLFILE=$(INSTALL) -m 0664

# Input files
SRCDIR=$(shell pwd -P)

.PHONY: clean multisite-qt

all:

install: installpython

installpython: 
	./setup.py install --prefix=$(PREFIX)

clean:

