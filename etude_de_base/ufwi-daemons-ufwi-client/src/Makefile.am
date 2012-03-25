bin_PROGRAMS = ufwi-client

ufwi_client_SOURCES = ufwi-client.c
ufwi_client_CPPFLAGS = @UFWICLIENTLIB_CFLAGS@ @UFWIBASE_CFLAGS@
ufwi_client_LDFLAGS = @UFWICLIENTLIB_LIBS@ @UFWIBASE_LIBS@

check:
	$(top_builddir)/src/ufwi-client -V
