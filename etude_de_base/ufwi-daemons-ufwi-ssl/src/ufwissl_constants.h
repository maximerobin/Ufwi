/*
 ** Copyright (C) 2007-2009 INL
 ** Written by S.Tricaud <stricaud@inl.fr>
 **            L.Defert <ldefert@inl.fr>
 ** INL http://www.inl.fr/
 **
 ** NuSSL: OpenSSL / GnuTLS layer based on libneon

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

#ifndef __UFWISSL_CONSTANTS__
#define __UFWISSL_CONSTANTS__

/* Context creation modes: */
typedef enum {
	UFWISSL_SSL_CTX_CLIENT,		/* client context */
	UFWISSL_SSL_CTX_SERVER,		/* default server context */
	UFWISSL_SSL_CTX_SERVERv2,		/* SSLv2 specific server context */
} ufwissl_mode_t;

typedef enum {
	UFWISSL_CERT_IGNORE,
	UFWISSL_CERT_REQUEST,
	UFWISSL_CERT_REQUIRE,
} ufwissl_cert_t;

typedef enum {
	UFWISSL_OK=0,		/*!< Success */
	UFWISSL_ERROR,		/*!< Generic error; use ufwissl_get_error(session) for message */
	UFWISSL_LOOKUP,		/*!< Server or proxy hostname lookup failed */
	UFWISSL_AUTH,		/*!< User authentication failed on server */
	UFWISSL_PROXYAUTH,	/*!< User authentication failed on proxy */
	UFWISSL_CONNECT,		/*!< Could not connect to server */
	UFWISSL_TIMEOUT,		/*!< Connection timed out */
	UFWISSL_FAILED,		/*!< The precondition failed */
	UFWISSL_RETRY,		/*!< Retry request (ufwissl_end_request ONLY) */
	UFWISSL_REDIRECT,		/*!< See ufwissl_redirect.h */
} ufwissl_error_t;

typedef enum {
	UFWISSL_SOCK_ERROR=-1,	/* Read/Write timed out */
	UFWISSL_SOCK_TIMEOUT=-2,	/* Socket was closed */
	UFWISSL_SOCK_CLOSED=-3,	/* Connection was reset (e.g. server crashed) */
	UFWISSL_SOCK_RESET=-4,	/* Secure connection was closed without proper SSL shutdown. */
	UFWISSL_SOCK_TRUNC=-5,
} ssl_sock_error_t;


/* Defined session flags: */
typedef enum ufwissl_session_flag_e {
	UFWISSL_SESSFLAG_PERSIST = 0,	/* disable this flag to prevent use of
					 * persistent connections. */

	UFWISSL_SESSFLAG_ICYPROTO,	/* enable this flag to enable support for
					 * non-HTTP ShoutCast-style "ICY" responses. */

	UFWISSL_SESSFLAG_SSLv2,	/* disable this flag to disable support for
				 * SSLv2, if supported by the SSL library. */

	UFWISSL_SESSFLAG_RFC4918,	/* enable this flag to enable support for
				 * RFC4918-only WebDAV features; losing
				 * backwards-compatibility with RFC2518
				 * servers. */

	UFWISSL_SESSFLAG_CONNAUTH,	/* enable this flag if an awful, broken,
					 * RFC-violating, connection-based HTTP
					 * authentication scheme is in use. */

	UFWISSL_SESSFLAG_TLS_SNI,	/* disable this flag to disable use of the
				 * TLS Server Name Indication extension. */

	UFWISSL_SESSFLAG_IGNORE_ID_MISMATCH,	/* Enable this flag to ignore mismatch
						 * between server FQDN and certificate CN value. */

	UFWISSL_SESSFLAG_LAST	/* enum sentinel value */
} ufwissl_session_flag;

#endif /* __UFWISSL_CONSTANTS__ */

