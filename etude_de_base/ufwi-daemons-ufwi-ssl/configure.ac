#                                               -*- Autoconf -*-
# Process this file with autoconf to produce a configure script.

AC_PREREQ(2.57)
AC_INIT(ufwi-ssl, 0.1.0, admin@ufwi.org)
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

# Global definitions
# _ISOC99_SOURCE	Use ISO C99 standard, needed by snprintf for example
# _GNU_SOURCE		Use GNU extensions like getline() in stdio.h
# _SVID_SOURCE		Needed to get 'strdup' from <string.h>
# _BSD_SOURCE		Use 4.3BSD

CFLAGS="$CFLAGS -D_ISOC99_SOURCE -D_GNU_SOURCE -D_BSD_SOURCE -D_SVID_SOURCE"

# check to see if struct dirent has the d_type member
AC_CHECK_MEMBER([struct dirent.d_type],
        [AC_DEFINE([HAVE_STRUCT_DIRENT_D_TYPE],
        [1],
        [Define if struct dirent has member d_type])],
        ,
        [#include <dirent.h>])

# Checks for libraries.

AC_CHECK_LIB([pthread], [pthread_mutex_init], check_pthread="yes", check_pthread="no")

#AC_CHECK_TOOL(DOCBOOK2MAN, docbook2man, true)
#AC_CHECK_TOOL(DOCBOOK2PDF, docbook2pdf, true)

# Checks for header files.
AC_HEADER_STDC
AC_CHECK_HEADERS([arpa/inet.h errno.h fcntl.h getopt.h limits.h netdb.h netinet/in.h netinet/tcp.h pthread.h stdarg.h stdlib.h string.h sys/select.h sys/socket.h unistd.h inexistent.h])

# Checks for typedefs, structures, and compiler characteristics.
AC_C_CONST

# Checks for library functions.
AC_FUNC_MALLOC
AC_FUNC_STAT
AC_CHECK_FUNCS([getopt_long gethostbyname memset setsockopt socket strcasecmp strspn])

#AC_CHECK_LIB([gcrypt], [gcry_md_open],AC_DEFINE([HAVE_LIBRARY_GCRYPT],[1],[Gcrypt lib flag]), check_gcrypt=no,[-L/usr/local/lib])
#AC_CHECK_LIB([gnutls], [gnutls_init],AC_DEFINE([HAVE_LIBRARY_GNUTLS],[1],[Gnutls lib flag]), check_gnutls=no)
#AM_CHECK_PATH([libgcrypt], [gcry_md_open],AC_DEFINE([HAVE_LIBRARY_GCRYPT],[1],[Gcrypt lib flag]), check_gcrypt=no,[-L/usr/local/lib])
#AM_CHECK_PATH(libgnutls], [gnutls_init],AC_DEFINE([HAVE_LIBRARY_GNUTLS],[1],[Gnutls lib flag]), check_gnutls=no)

PKG_PROG_PKG_CONFIG

dnl
dnl <SSL>
dnl

dnl We can force the use of OpenSSL
AC_ARG_WITH(openssl,   [AC_HELP_STRING(--with-openssl, Build with openssl support *EXPERIMENTAL*.)],build_openssl=$enableval, build_openssl="no" )

if test "${build_openssl}" != "no"; then
   PKG_CHECK_MODULES(OPENSSL, openssl)
   AC_DEFINE_UNQUOTED([HAVE_OPENSSL],[1],[Will use openssl support instead of gnutls])
else
   NEED_LIBGCRYPT_VERSION=1.2.0
   AM_PATH_LIBGCRYPT("$NEED_LIBGCRYPT_VERSION")
   if test "x$LIBGCRYPT_LIBS" = "x"; then
     AC_MSG_ERROR([libgcrypt is needed.
                     See ftp://ftp.gnupg.org/gcrypt/ .])
   else
     CFLAGS="$CFLAGS $LIBGCRYPT_CFLAGS"
     LDFLAGS="$LDFLAGS $LIBGCRYPT_LIBS"
   fi

   NEED_LIBGNUTLS_VERSION=1.0.16
   PKG_CHECK_MODULES(GNUTLS, gnutls >= $NEED_LIBGNUTLS_VERSION,,exit)
   AC_DEFINE_UNQUOTED([HAVE_GNUTLS],[1],[Will use gnutls support instead of openssl])
   AC_CHECK_LIB(gnutls, gnutls_priority_set, AC_DEFINE_UNQUOTED(HAVE_GNUTLS_STRING_PRIORITY, , Define whether GnuTLS provide priority parsing),)
fi
dnl
dnl </SSL>
dnl

define([EXPAND_VARIABLE],
[$2=[$]$1
while true; do
  case "[$]$2" in
    *\[$]* ) eval "$2=[$]$2" ;;
    *) break ;;
  esac
done])dnl EXPAND_VARIABLE


AC_ARG_ENABLE(debug,   [AC_HELP_STRING(--enable-debug, Add development debug messages (default no))],debug=$enableval, debug="")

AC_CHECK_HEADERS([ev.h])
AC_CHECK_LIB([ev], [ev_loop], have_libev="yes",AC_MSG_ERROR([libev is required to build ufwi-ssl]))

AM_CONDITIONAL(USE_OPENSSL, test x$build_openssl != xno)
AM_CONDITIONAL(USE_GNUTLS, test x$build_openssl = xno)

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
        src/libufwissl.pc
])

# Display errors if any library is missing
if test \
    -o x${check_gcrypt} = xno \
    -o x${check_gnutls} = xno \
; then
    AC_MSG_RESULT([])
    if test x${check_gcrypt} = xno; then
        AC_MSG_RESULT([ERROR: gcrypt library needed for encryption])
    fi
    if test x${check_gnutls} = xno; then
        AC_MSG_RESULT([ERROR: gnutls library needed for encryption])
    fi
    exit 1
fi

AM_INIT_AUTOMAKE(1.8)

AC_OUTPUT
AC_MSG_RESULT([

Configuration complete
])

if test "$debug"; then
	AC_MSG_RESULT([* Compiling with developement DEBUG support])
fi

if test "${build_openssl}" != "no"; then
	AC_MSG_RESULT([* Compiling with OpenSSL])
else
	AC_MSG_RESULT([* Compiling with GnuTLS])
fi

AC_MSG_RESULT([
Now type 'make' and then 'sudo make install'])

