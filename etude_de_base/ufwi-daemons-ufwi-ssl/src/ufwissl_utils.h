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

#ifndef UFWISSL_UTILS_H
#define UFWISSL_UTILS_H

#include <sys/types.h>

#include <stdarg.h>
#include <stdio.h>

#include "ufwissl_config.h"
#include "ufwissl_constants.h"
#include "ufwissl_defs.h"

#ifdef NEON_TRIO
#include <trio.h>
#endif

UFWISSL_BEGIN_DECLS
/* Returns a human-readable library version string describing the
 * version and build information; for example:
 *    "neon 0.2.0: Library build, OpenSSL support" */
const char *ufwissl_version_string(void);

/* Returns non-zero if library version is not of major version
 * 'major', or if minor version is not greater than or equal to
 * 'minor'.  For neon versions with major == 0, all minor versions are
 * presumed to be incompatible.  */
int ufwissl_version_match(int major, int minor);

/* Feature codes: */
#define UFWISSL_FEATURE_SSL (1)	/* SSL/TLS support */
#define UFWISSL_FEATURE_ZLIB (2)	/* zlib compression in compress interface */
#define UFWISSL_FEATURE_IPV6 (3)	/* IPv6 is supported in resolver */
#define UFWISSL_FEATURE_LFS (4)	/* large file support */
#define UFWISSL_FEATURE_SOCKS (5)	/* SOCKSv5 support */
#define UFWISSL_FEATURE_TS_SSL (6)	/* Thread-safe SSL/TLS support */
#define UFWISSL_FEATURE_I18N (7)	/* i18n error message support */

/* Returns non-zero if library is built with support for the given
 * UFWISSL_FEATURE_* feature code 'code'. */
int ufwissl_has_support(int feature);

/* Debugging macro to allow code to be optimized out if debugging is
 * disabled at build time. */
#if 0
#ifndef UFWISSL_DEBUGGING
#define UFWISSL_DEBUG if (0) ufwissl_debug
#else				/* DEBUGGING */
#define UFWISSL_DEBUG ufwissl_debug
#endif				/* DEBUGGING */
#endif



/* Debugging masks. */
#if 0
#define UFWISSL_DBG_SOCKET (1<<0)	/* raw socket */
#define UFWISSL_DBG_HTTP (1<<1)	/* HTTP request/response handling */
#define UFWISSL_DBG_XML (1<<2)	/* XML parser */
#define UFWISSL_DBG_HTTPAUTH (1<<3)	/* HTTP authentication (hiding credentials) */
#define UFWISSL_DBG_HTTPPLAIN (1<<4)	/* plaintext HTTP authentication */
#define UFWISSL_DBG_LOCKS (1<<5)	/* WebDAV locking */
#define UFWISSL_DBG_XMLPARSE (1<<6)	/* low-level XML parser */
#define UFWISSL_DBG_HTTPBODY (1<<7)	/* HTTP response body blocks */
#define UFWISSL_DBG_SSL (1<<8)	/* SSL/TLS */
#define UFWISSL_DBG_FLUSH (1<<30)	/* always flush debugging */
#endif

#define UFWISSL_DEBUG fprintf

#define UFWISSL_DBG_SOCKET stderr
#define UFWISSL_DBG_HTTP stderr
#define UFWISSL_DBG_XML stderr
#define UFWISSL_DBG_HTTPAUTH stderr
#define UFWISSL_DBG_HTTPPLAIN stderr
#define UFWISSL_DBG_LOCKS stderr
#define UFWISSL_DBG_XMLPARSE stderr
#define UFWISSL_DBG_HTTPBODY stderr
#define UFWISSL_DBG_SSL stderr
#define UFWISSL_DBG_FLUSH stderr



/* Send debugging output to 'stream', for all of the given debug
 * channels.  To disable debugging, pass 'stream' as NULL and 'mask'
 * as 0. */
void ufwissl_debug_init(FILE * stream, int mask);

/* The current debug mask and stream set by the last call to
 * ufwissl_debug_init. */
extern int ufwissl_debug_mask;
extern FILE *ufwissl_debug_stream;

/* Produce debug output if any of channels 'ch' is enabled for
 * debugging. */
void ufwissl_debug(int ch, const char *,
		 ...) ufwissl_attribute((format(printf, 2, 3)));

/* Storing an HTTP status result */
typedef struct {
	int major_version;
	int minor_version;
	int code;		/* Status-Code value */
	int klass;		/* Class of Status-Code (1-5) */
	char *reason_phrase;
} ufwissl_status;

/* NB: couldn't use 'class' in ufwissl_status because it would clash with
 * the C++ reserved word. */

int check_key_perms(const char *filename);

UFWISSL_END_DECLS
#endif				/* UFWISSL_UTILS_H */
