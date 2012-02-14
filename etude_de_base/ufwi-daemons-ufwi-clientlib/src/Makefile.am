SUBDIRS = plugins

lib_LTLIBRARIES = libufwiclient.la

EXTRA_DIST = checks.h getdelim.h internal.h libufwiclient.h \
			 proc.h sys_config.h sending.h tcptable.h \
			 nuclient_conf.h ufwiclient_plugins.h

include_HEADERS = ufwiclient.h

libufwiclient_la_SOURCES = ${include_HEADERS} libufwiclient.c proc.c iconv.c checks.c getdelim.c sending.c \
			 sys_config.c tcptable.c internal.c \
			 nuclient_conf.c ufwiclient_plugins.c


libufwiclient_la_LIBADD = -lsasl2 @UFWIBASE_LIBS@ @UFWISSL_LIBS@ @UFWICONFPARSER_LIBS@
libufwiclient_la_CFLAGS = -DCONFIG_DIR=\"$(sysconfdir)\" -DMODULES_DIR=\"$(libdir)/ufwiclient/modules/\" @UFWIBASE_CFLAGS@ @UFWISSL_CFLAGS@ @UFWICONFPARSER_CFLAGS@

libufwiclient_la_LDFLAGS=-version-info 0:1:0

includedir = $(prefix)/include/ufwiclient
pkgconfigdir = $(libdir)/pkgconfig
pkgconfig_DATA = libufwiclient.pc
