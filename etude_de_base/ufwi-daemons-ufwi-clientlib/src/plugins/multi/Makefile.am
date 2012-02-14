# postauth_locamulti plugin

AM_CFLAGS = -DCONFIG_DIR=\"$(sysconfdir)\" -DMODULE_DIR=\"$(libdir)\"
INCLUDES = @UFWIBASE_CFLAGS@ @UFWISSL_CFLAGS@ @UFWICONFPARSER_LIBS@
plugindir = $(libdir)/ufwiclient/modules

plugin_LTLIBRARIES = multi.la

multi_la_SOURCES = multi_main.c
multi_la_LDFLAGS = -module -avoid-version @UFWIBASE_LIBS@ @UFWISSL_CFLAGS@ @UFWICONFPARSER_CFLAGS@

multi.la: $(multi_la_OBJECTS) $(multi_la_DEPENDENCIES)
	$(LINK) -rpath $(plugindir) $(multi_la_LDFLAGS) $(multi_la_OBJECTS) $(multi_la_LIBADD)
