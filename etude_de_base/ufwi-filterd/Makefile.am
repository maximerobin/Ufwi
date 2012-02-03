SUBDIRS = src selinux conf

EXTRA_DIST = autogen.sh

all:
	@echo "Compile done";

install-conf:
	install -d $(sysconfdir)
	test -e $(sysconfdir)/ufwi-filterd || install -d -m 700 $(sysconfdir)/ufwi-filterd/
	test -e $(sysconfdir)/ufwi-filterd/filterd.conf || install -m 600 $(top_srcdir)/conf/filterd.conf $(sysconfdir)/ufwi-filterd/
