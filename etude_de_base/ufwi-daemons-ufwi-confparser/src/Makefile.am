lib_LTLIBRARIES = libufwiconfparser.la
include_HEADERS = config-parser.h

EXTRA_DIST = config-parser.h t1.conf t1_included.conf

BUILT_SOURCES = config-parser.yacc.h
AM_YFLAGS = -d

AM_CPPFLAGS = @UFWIBASE_CFLAGS@
libufwissl_la_libadd = @UFWIBASE_LIBS@

libufwiconfparser_la_SOURCES =		\
		config-parser.yacc.y	\
		config-parser.lex.l

includedir = $(prefix)/include/ufwiconfparser
pkgconfigdir = $(libdir)/pkgconfig
pkgconfig_DATA = libufwiconfparser.pc

check_PROGRAMS = t_conf1 t_conf2 t_conf3

TESTS = ${check_PROGRAMS}

t_conf1_SOURCES = t_conf1.c
t_conf1_LDADD = @UFWIBASE_LIBS@

t_conf2_SOURCES = t_conf2.c
t_conf2_LDADD = @UFWIBASE_LIBS@

t_conf3_SOURCES = t_conf3.c
t_conf3_LDADD = @UFWIBASE_LIBS@

