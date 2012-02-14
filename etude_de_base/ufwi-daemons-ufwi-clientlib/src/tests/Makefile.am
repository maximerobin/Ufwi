EXTRA_DIST = dummy_client.c

check:
	gcc -o dummy_client $(srcdir)/dummy_client.c @UFWIBASE_CFLAGS@ @UFWISSL_CFLAGS@ @UFWICONFPARSER_CFLAGS@ -I$(top_srcdir)/src/ @UFWIBASE_LIBS@ @UFWISSL_LIBS@ @UFWICONFPARSER_LIBS@ -lnuclient
	rm dummy_client
