/*
 ** Copyright (C) 2007-2009 INL
 ** Written by S.Tricaud <stricaud@inl.fr>
 **            L.Defert <ldefert@inl.fr>
 ** INL http://www.inl.fr/
 **
 ** NuSSL: OpenSSL / GnuTLS layer based on libneon
 */


/*
   HTTP utility functions
   Copyright (C) 1999-2006, Joe Orton <joe@manyfish.co.uk>

   This library is free software; you can redistribute it and/or
   modify it under the terms of the GNU Library General Public
   License as published by the Free Software Foundation; either
   version 3 of the License, or (at your option) any later version.

   This library is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
   Library General Public License for more details.

   You should have received a copy of the GNU Library General Public
   License along with this library; if not, write to the Free
   Software Foundation, Inc., 59 Temple Place - Suite 330, Boston,
   MA 02111-1307, USA

   In addition, as a special exception, INL
   gives permission to link the code of its release of NuSSL with the
   OpenSSL project's "OpenSSL" library (or with modified versions of it
   that use the same license as the "OpenSSL" library), and distribute
   the linked executables.  You must obey the GNU General Public License
   in all respects for all of the code used other than "OpenSSL".  If you
   modify this file, you may extend this exception to your version of the
   file, but you are not obligated to do so.  If you do not wish to do
   so, delete this exception statement from your version.
*/

#include "ufwissl_config.h"

#include <sys/types.h>

#include <string.h>

#include <stdio.h>
#include <ctype.h>		/* isdigit() for ufwissl_parse_statusline */

#ifdef UFWISSL_HAVE_ZLIB
#include <zlib.h>
#endif

#ifdef HAVE_OPENSSL
#include <openssl/opensslv.h>
#endif

#ifdef HAVE_GNUTLS
#include <gnutls/gnutls.h>
#endif

/* libxml2: pick up the version string. */
#if defined(HAVE_LIBXML)
#include <libxml/xmlversion.h>
#elif defined(HAVE_EXPAT) && !defined(HAVE_XMLPARSE_H)
#include <expat.h>
#endif

#include <sys/types.h>
#include <sys/stat.h>
#ifdef HAVE_UNISTD_H
# include <unistd.h>
#endif


#include "ufwissl_utils.h"
#include "ufwissl_string.h"	/* for ufwissl_strdup */
#include "ufwissl_dates.h"

int ufwissl_debug_mask = 0;
FILE *ufwissl_debug_stream = NULL;

void ufwissl_debug_init(FILE * stream, int mask)
{
	ufwissl_debug_stream = stream;
	ufwissl_debug_mask = mask;
#if defined(HAVE_SETVBUF) && defined(_IONBF)
	/* If possible, turn off buffering on the debug log.  this is very
	 * helpful if debugging segfaults. */
	if (stream)
		setvbuf(stream, NULL, _IONBF, 0);
#endif
}

void ufwissl_debug(int ch, const char *template, ...)
{
	va_list params;
	if ((ch & ufwissl_debug_mask) == 0)
		return;
	fflush(stdout);
	va_start(params, template);
	vfprintf(ufwissl_debug_stream, template, params);
	va_end(params);
/*    if ((ch & UFWISSL_DBG_FLUSH) == UFWISSL_DBG_FLUSH)
	fflush(ufwissl_debug_stream);*/
}

#define UFWISSL_STRINGIFY(x) # x
#define UFWISSL_EXPAT_VER(x,y,z) UFWISSL_STRINGIFY(x) "." UFWISSL_STRINGIFY(y) "." UFWISSL_STRINGIFY(z)

static const char version_string[] = "neon " NEON_VERSION ": "
#ifdef NEON_IS_LIBRARY
    "Library build"
#else
    "Bundled build"
#endif
#ifdef UFWISSL_HAVE_IPV6
    ", IPv6"
#endif
#ifdef HAVE_EXPAT
    ", Expat"
/* expat >=1.95.2 exported the version */
#ifdef XML_MAJOR_VERSION
    " " UFWISSL_EXPAT_VER(XML_MAJOR_VERSION, XML_MINOR_VERSION,
			XML_MICRO_VERSION)
#endif
#else				/* !HAVE_EXPAT */
#ifdef HAVE_LIBXML
    ", libxml " LIBXML_DOTTED_VERSION
#endif				/* HAVE_LIBXML */
#endif				/* !HAVE_EXPAT */
#if defined(UFWISSL_HAVE_ZLIB) && defined(ZLIB_VERSION)
    ", zlib " ZLIB_VERSION
#endif				/* UFWISSL_HAVE_ZLIB && ... */
#ifdef UFWISSL_HAVE_SOCKS
    ", SOCKSv5"
#endif
#ifdef HAVE_OPENSSL
#ifdef OPENSSL_VERSION_TEXT
    ", " OPENSSL_VERSION_TEXT
#else
    "OpenSSL (unknown version)"
#endif				/* OPENSSL_VERSION_TEXT */
#endif				/* HAVE_OPENSSL */
#ifdef HAVE_GNUTLS
    ", GNU TLS " LIBGNUTLS_VERSION
#endif				/* HAVE_GNUTLS */
    ".";

const char *ufwissl_version_string(void)
{
	return version_string;
}

int ufwissl_version_match(int major, int minor)
{
	return UFWISSL_VERSION_MAJOR != major || UFWISSL_VERSION_MINOR < minor
	    || (UFWISSL_VERSION_MAJOR == 0 && UFWISSL_VERSION_MINOR != minor);
}

int ufwissl_has_support(int feature)
{
	switch (feature) {
#if defined(UFWISSL_HAVE_ZLIB) || defined(UFWISSL_HAVE_IPV6) \
    || defined(UFWISSL_HAVE_SOCKS) || defined(UFWISSL_HAVE_LFS) \
    || defined(UFWISSL_HAVE_TS_SSL) || defined(UFWISSL_HAVE_I18N)
	case UFWISSL_FEATURE_SSL:
#ifdef UFWISSL_HAVE_ZLIB
	case UFWISSL_FEATURE_ZLIB:
#endif
#ifdef UFWISSL_HAVE_IPV6
	case UFWISSL_FEATURE_IPV6:
#endif
#ifdef UFWISSL_HAVE_SOCKS
	case UFWISSL_FEATURE_SOCKS:
#endif
#ifdef UFWISSL_HAVE_LFS
	case UFWISSL_FEATURE_LFS:
#endif
#ifdef UFWISSL_HAVE_TS_SSL
	case UFWISSL_FEATURE_TS_SSL:
#endif
#ifdef UFWISSL_HAVE_I18N
	case UFWISSL_FEATURE_I18N:
#endif
		return 1;
#endif				/* UFWISSL_HAVE_* */
	default:
		return 0;
	}
}

int check_key_perms(const char *filename)
{
	struct stat info;

	if (stat(filename, &info) != 0)
		return UFWISSL_ERROR;

#ifndef _WIN32
	/* File should not be readable or writable by others */
	if (info.st_mode & S_IROTH || info.st_mode & S_IWOTH)
		return UFWISSL_ERROR;
#endif

	return UFWISSL_OK;
}
