lib_LTLIBRARIES = libufwissl.la

EXTRA_DIST = README

# headers to be installed
include_HEADERS = ufwissl.h ufwissl_constants.h ufwissl_hash.h

# headers required for build
noinst_libufwissl_la_SOURCES = ufwissl_alloc.h ufwissl_config.h \
	ufwissl_dates.h ufwissl_defs.h ufwissl_internal.h \
	ufwissl_private.h ufwissl_privssl.h ufwissl_request.h \
	ufwissl_session.h ufwissl_socket.h \
	ufwissl_ssl_common.h ufwissl_ssl.h ufwissl_string.h ufwissl_utils.h

# sources
libufwissl_la_SOURCES = ufwissl_alloc.c ufwissl_dates.c ufwissl_openssl.c \
	ufwissl_openssl_ctx.c ufwissl_gnutls.c ufwissl_gnutls_ctx.c \
	ufwissl_ssl_common.c ufwissl_request.c ufwissl_session.c ufwissl_socket.c \
	ufwissl_string.c ufwissl_utils.c \
	ufwissl_openssl_local.c ufwissl_gnutls_local.c \
	ufwissl_hash.c \
	${include_HEADERS} \
	${noinst_libufwissl_la_SOURCES}
AM_CPPFLAGS = -D_REENTRANT

if USE_OPENSSL
AM_CFLAGS=$(AM_CPPFLAGS) @OPENSSL_CFLAGS@
libufwissl_la_LIBADD = -lpthread @OPENSSL_LIBS@
else
libufwissl_la_LIBADD = -lpthread -lgcrypt -lgnutls
endif

libufwissl_la_LDFLAGS = -version-info 0:1:0 -lev

includedir = $(prefix)/include/ufwissl
pkgconfigdir = $(libdir)/pkgconfig
pkgconfig_DATA = libufwissl.pc

bin_PROGRAMS = ufwissl_tool

ufwissl_tool_SOURCES = ufwissl_tool.c
ufwissl_tool_LDADD = ./libufwissl.la

