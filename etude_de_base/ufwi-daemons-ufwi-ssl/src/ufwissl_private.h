/*
 ** Copyright (C) 2007-2009 INL
 ** Written by S.Tricaud <stricaud@inl.fr>
 **            L.Defert <ldefert@inl.fr>
 **            Pierre Chifflier <chifflier@inl.fr>
 ** INL http://www.inl.fr/
 **
 ** NuSSL: OpenSSL / GnuTLS layer based on libneon
 */


/*
   HTTP Request Handling
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

/* THIS IS NOT A PUBLIC INTERFACE. You CANNOT include this header file
 * from an application.  */

#ifndef UFWISSL_PRIVATE_H
#define UFWISSL_PRIVATE_H

/* #include "ufwissl_request.h" */
#include "ufwissl_socket.h"
#include "ufwissl_ssl.h"

struct host_info {
	char *hostname;
	unsigned int port;
	ufwissl_sock_addr *address;	/* if non-NULL, result of resolving 'hostname'. */
	/* current network address obtained from 'address' being used. */
	const ufwissl_inet_addr *current;
};

/* Store every registered callback in a generic container, and cast
 * the function pointer when calling it.  */
struct hook {
	void (*fn) (void);
	void *userdata;
	const char *id;		/* non-NULL for accessors. */
	struct hook *next;
};

#define HAVE_HOOK(st,func) (st->hook->hooks->func != NULL)
#define HOOK_FUNC(st, func) (*st->hook->hooks->func)

/* Session support. */
struct ufwissl_session_s {
	/* Connection information */
	ufwissl_socket *socket;

	/* non-zero if connection has persisted beyond one request. */
	int persisted;

	struct host_info server;

	/* application-provided address list */
	const ufwissl_inet_addr **addrlist;
	size_t numaddrs, curaddr;

	int flags[UFWISSL_SESSFLAG_LAST];

	int rdtimeout, cotimeout;	/* read, connect timeouts. */


/* rename into my_cert & peer_cert */
	ufwissl_ssl_client_cert *my_cert;
	ufwissl_ssl_certificate *peer_cert;
	ufwissl_ssl_context *ssl_context;

#if 0
	/* Server cert verification callback: */
	ufwissl_ssl_verify_fn ssl_verify_fn;
	void *ssl_verify_ud;
	/* Client cert provider callback: */
	ufwissl_ssl_provide_fn ssl_provide_fn;
	void *ssl_provide_ud;
#endif

	ufwissl_session_status_info status;

	int check_peer_cert;

	/* UFWISSL_SSL_CTX_SERVER or UFWISSL_SSL_CTX_CLIENT */
	int mode;

	/* Error string */
	char error[512];
};

#if 0
/* Pushes block of 'count' bytes at 'buf'. Returns non-zero on
 * error. */
typedef int (*ufwissl_push_fn) (void *userdata, const char *buf,
			      size_t count);
#endif

/* Generate DH prime number. */
int ufwissl_ssl_create_dh_params(ufwissl_session * sess, unsigned int dh_bits);

/* Do the SSL negotiation. */
int ufwissl__negotiate_ssl(ufwissl_session * sess);

/* Set the session error appropriate for SSL verification failures. */
void ufwissl__ssl_set_verify_err(ufwissl_session * sess, int failures);

/* Check certificates after the SSL handshake */
int ufwissl__ssl_post_handshake(ufwissl_session * sess);
#endif				/* HTTP_PRIVATE_H */
