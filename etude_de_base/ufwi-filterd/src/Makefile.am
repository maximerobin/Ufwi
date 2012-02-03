AM_CPPFLAGS = -DLOCAL_STATE_DIR=\"$(localstatedir)\"  -DCONFIG_DIR=\"$(sysconfdir)/ufwi-filterd/\" @UFWIBASE_CFLAGS@ @UFWISSL_CFLAGS@ @UFWICONFPARSER_CFLAGS@
AM_LDFLAGS = @UFWIBASE_LIBS@ @UFWISSL_LIBS@ @UFWICONFPARSER_LIBS@
sbin_PROGRAMS = ufwi-filterd

# nufw

noinst_ufwi_filterd_SOURCES = iface.h nufw.h structure.h nufwconf.h

ufwi_filterd_SOURCES = authsrv.c  common.c  main.c  packetsrv.c \
		tls.c audit.c iface.c \
		nufwconf.c \
		${noinst_ufwi_filterd_SOURCES}

if HAVE_NFQUEUE_ONLY
ufwi_filterd_LDADD = -lnfnetlink -lnetfilter_queue
endif

#
#ufwi_filterd$(EXEEXT): $(ufwi_literd_OBJECTS) $(ufwi_filterd_DEPENDENCIES)
#	@rm -f ufwi_filterd$(EXEEXT)
#	$(LINK) $(ufwi_filterd_LDFLAGS) $(w_OBJECTS) $(ufwi_filterd_LDADD)
