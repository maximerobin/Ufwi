# postauth_localuser plugin

AM_CFLAGS = -DCONFIG_DIR=\"$(sysconfdir)\" -DMODULE_DIR=\"$(libdir)\"
INCLUDES = @UFWIBASE_CFLAGS@ @UFWISSL_CFLAGS@ @UFWICONFPARSER_CFLAGS@
plugindir = $(libdir)/ufwiclient/modules

plugin_LTLIBRARIES = luser.la

luser_la_SOURCES = luser_main.c
luser_la_LDFLAGS = -module -avoid-version @UFWIBASE_LIBS@ @UFWISSL_CFLAGS@ @UFWICONFPARSER_CFLAGS@

luser.la: $(luser_la_OBJECTS) $(luser_la_DEPENDENCIES)
	$(LINK) -rpath $(plugindir) $(luser_la_LDFLAGS) $(luser_la_OBJECTS) $(luser_la_LIBADD)
