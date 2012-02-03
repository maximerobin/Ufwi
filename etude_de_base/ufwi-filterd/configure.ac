#                                               -*- Autoconf -*-
# Process this file with autoconf to produce a configure script.

AC_PREREQ(2.57)
AC_INIT(ufwi-filterd, 0.1.0, admin@ufwi.org)
AM_CONFIG_HEADER(src/config.h)

# Checks for programs.
AC_PROG_CC

# check for a ISO C99 compiler
AC_DEFUN([AC_CPP_FUNC], [AC_REQUIRE([AC_PROG_CC_STDC])dnl
AC_CACHE_CHECK([for an ANSI C99-conforming __func__], ac_cv_cpp_func,
[AC_COMPILE_IFELSE([AC_LANG_PROGRAM([],
[[char *foo = __func__;]])],
  [ac_cv_cpp_func=yes],
  [AC_COMPILE_IFELSE([AC_LANG_PROGRAM([],
[[char *foo = __FUNCTION__;]])],
  [ac_cv_cpp_func=__FUNCTION__],
  [ac_cv_cpp_func=no])])])

if test $ac_cv_cpp_func = yes; then
   AC_DEFINE(__PRELUDE_FUNC__, __func__, [Define to __FUNCTION__ or "" if '__func__' does not conform to ANSI C.])
elif test $ac_cv_cpp_func = __FUNCTION__; then
   AC_DEFINE(__PRELUDE_FUNC__, __FUNCTION__, [Define to __FUNCTION__ or "" if '__func__' does not conform to ANSI C.])
elif test $ac_cv_cpp_func = no; then
   AC_DEFINE(__PRELUDE_FUNC__, "", [Define to __FUNCTION__ or "" if '__func__' does not conform to ANSI C.])
fi
])

AC_CPP_FUNC

AM_PROG_LIBTOOL
AC_PROG_INSTALL

# Checks for endianess
AC_C_BIGENDIAN()

case $host in
*-*-linux*)
	AC_DEFINE([LINUX],[1],[Target is Linux])
	CFLAGS="$CFLAGS -D_POSIX_C_SOURCE=199506L" ;;
*-*-darwin*) AC_DEFINE([FREEBSD],[1],[Target is darwin (freebsd like)]) ;;
*-*-freebsd*) AC_DEFINE([FREEBSD],[1],[Target is freebsd]) ;;
*) AC_MSG_ERROR([Linux, FreeBSD, Darwin only, dude!]);;
esac

CFLAGS="$CFLAGS -D_ISOC99_SOURCE -D_GNU_SOURCE -D_BSD_SOURCE -D_SVID_SOURCE"

# check to see if struct dirent has the d_type member
AC_CHECK_MEMBER([struct dirent.d_type],
        [AC_DEFINE([HAVE_STRUCT_DIRENT_D_TYPE],
        [1],
        [Define if struct dirent has member d_type])],
        ,
        [#include <dirent.h>])

# Checks for libraries.

AC_CHECK_TOOL(DOCBOOK2MAN, docbook2man, true)
AC_CHECK_TOOL(DOCBOOK2PDF, docbook2pdf, true)

# Checks for header files.
AC_HEADER_STDC
AC_CHECK_HEADERS([arpa/inet.h errno.h fcntl.h getopt.h limits.h netdb.h netinet/in.h netinet/tcp.h pthread.h stdarg.h stdlib.h string.h sys/select.h sys/socket.h unistd.h inexistent.h])

# Checks for typedefs, structures, and compiler characteristics.
AC_C_CONST

# Checks for library functions.
AC_FUNC_MALLOC
AC_FUNC_STAT
AC_CHECK_FUNCS([getopt_long gethostbyname memset setsockopt socket strcasecmp strspn])

PKG_PROG_PKG_CONFIG

PKG_CHECK_MODULES(UFWIBASE, libufwibase)
PKG_CHECK_MODULES(UFWISSL, libufwissl)
PKG_CHECK_MODULES(UFWICONFPARSER, libufwiconfparser)

AC_ARG_WITH(nfqueue,   [AC_HELP_STRING(--without-nfqueue, Compile for QUEUE instead of NFQUEUE)],use_nfqueue=$withval, use_nfqueue="yes")
AC_ARG_WITH(fixedtimeout,   [AC_HELP_STRING(--with-fixedtimeout, Assume libconntrack has fixed timeout extension )],have_conntrack_fixedtimeout=$withval )

define([EXPAND_VARIABLE],
[$2=[$]$1
while true; do
  case "[$]$2" in
    *\[$]* ) eval "$2=[$]$2" ;;
    *) break ;;
  esac
done])dnl EXPAND_VARIABLE

AC_ARG_ENABLE(debug,   [AC_HELP_STRING(--enable-debug, Add development debug messages (default no))],debug=$enableval, debug="")
AC_ARG_WITH(perf-display,
    [AC_HELP_STRING(--without-perf-display, Disable performance display)],
    use_perf_display=$withval, use_perf_display="yes")

if test "${use_perf_display}" = "yes"; then
	AC_DEFINE_UNQUOTED([PERF_DISPLAY_ENABLE],[1],[Performance display])
fi

if test "${use_nfqueue}" = "yes"; then
    # if we don't have we can't build nufw
    AC_CHECK_LIB([nfnetlink], [nfnl_open], have_nfqueue="yes", build_nufw="")
    AC_CHECK_LIB([netfilter_queue], [nfq_open], have_nfqueue="yes",[AC_MSG_ERROR([libnetfilter_queue not present])],[-lnfnetlink])
    AC_CHECK_LIB([netfilter_queue], [nfq_set_queue_maxlen],AC_DEFINE_UNQUOTED([HAVE_NFQ_SET_QUEUE_MAXLEN],[1],[Found queue max length support in netfilter_queue]) ,,[-lnfnetlink])
    AC_CHECK_LIB([netfilter_queue], [nfq_set_verdict_mark_exptime],AC_DEFINE_UNQUOTED([HAVE_NFQ_MARK_EXPTIME],[1],[Found verdict with mark and exptime support in netfilter_queue]) ,,[-lnfnetlink])
    AC_CHECK_LIB([nfnetlink], [nlif_catch],
    		AC_CHECK_LIB([netfilter_queue], [nfq_get_indev_name],
    			AC_DEFINE_UNQUOTED([HAVE_NFQ_INDEV_NAME],
    				[1],
    				[Found iface resolution in nfnetlink and libnetfilter_queue]),
    			AC_MSG_WARN("Support of interface resolution in nfnetlink but not in netfilter_queue"),
    			[-lnfnetlink])
    	    )
    AC_DEFINE_UNQUOTED([USE_NFQUEUE],[1],[Will use netlink queue])
fi

AM_CONDITIONAL(USE_USER_MARK, test x$enable_user_mark = xyes)
AM_CONDITIONAL(HAVE_NFQUEUE_ONLY, test x$have_nfqueue = xyes && test x$have_conntrack = x  )

if test "x$GCC" = "xyes"; then

	dnl get gcc version
	AC_MSG_CHECKING([gcc version])
		gccver=$($CC -dumpversion)
		gccvermajor=$(echo $gccver | cut -d . -f1)
		gccverminor=$(echo $gccver | cut -d . -f2)
		gccvernum=$(expr $gccvermajor "*" 100 + $gccverminor)
	AC_MSG_RESULT($gccver)


	if test "$gccvernum" -ge "400"; then
		dnl gcc 4.0 or later
		CFLAGS="$CFLAGS -Wextra"
	else
		CFLAGS="$CFLAGS -W"
	fi
fi

CFLAGS="$CFLAGS -Wall"
CFLAGS="$CFLAGS -Wno-unused-parameter"

if test "${debug}" = "yes"; then
	AC_DEFINE_UNQUOTED([DEBUG_ENABLE],[1],[Will compile development debug message])
	CFLAGS="$CFLAGS -O0 -g"
else
	CFLAGS="$CFLAGS -O2"
fi

# get revision
if test -f ./revision; then
    REVISION=`cat ./revision`
    CFLAGS="${CFLAGS} -DREVISION=\"${REVISION}\""
else
    GIT=`which git`
    if test "$GIT" != ""; then
        REVISION=`git rev-parse --short HEAD`
        CFLAGS="${CFLAGS} -DREVISION=\"${REVISION}\""
    fi
fi

AC_CONFIG_FILES([Makefile
        src/Makefile
        conf/Makefile
        selinux/Makefile
])

AM_INIT_AUTOMAKE(1.8)

AC_OUTPUT
AC_MSG_RESULT([

Configuration complete
])

if test "$debug"; then
	AC_MSG_RESULT([* Compiling with developement DEBUG support])
fi

if test "${have_nfqueue}" = "yes"; then
	AC_MSG_RESULT([  - NuFW: libnetfilter_queue support])
fi

AC_MSG_RESULT([
Now type 'make' and then 'sudo make install'])

