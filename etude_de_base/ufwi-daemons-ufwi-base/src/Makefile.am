lib_LTLIBRARIES = libufwibase.la

include_HEADERS = linuxlist.h config-table.h ipv6.h log.h ufwibase.h packet_parser.h strings.h ext_proto.h \
		security.h debug.h documentation.h jhash.h ufwi_source.h proto.h \
		proto_v3.h proto_v4.h proto_v5.h security.h

libufwibase_la_SOURCES = config-table.c	\
		log.c			\
		ipv6.c			\
		packet_parser.c		\
		strings.c		\
		ext_proto.c		\
		${include_HEADERS}

libufwibase_la_LDFLAGS = -version-info 0:1:0
includedir = $(prefix)/include/ufwibase
pkgconfigdir = $(libdir)/pkgconfig
pkgconfig_DATA = libufwibase.pc
