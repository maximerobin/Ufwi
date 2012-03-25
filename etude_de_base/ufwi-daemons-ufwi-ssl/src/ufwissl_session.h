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
   HTTP session handling
   Copyright (C) 1999-2007, Joe Orton <joe@manyfish.co.uk>

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

#ifndef UFWISSL_SESSION_H
#define UFWISSL_SESSION_H 1

#include <sys/types.h>

#include "ufwissl_ssl.h"
/* #include "ufwissl_uri.h" /\* for ufwissl_uri *\/ */
#include "ufwissl_defs.h"
#include "ufwissl_socket.h"
#include "ufwissl_constants.h"
#include "ufwissl_privssl.h"

UFWISSL_BEGIN_DECLS typedef struct ufwissl_session_s ufwissl_session;

/* Create a session to the given server, using the given mode.
 * mode can be one of UFWISSL_SSL_CTX_CLIENT, UFWISSL_SSL_CTX_SERVER,
 * or UFWISSL_SSL_CTX_SERVERv2 */
ufwissl_session *ufwissl_session_create(int mode);

void ufwissl_session_destroy(ufwissl_session * sess);

/* Prematurely force the connection to be closed for the given
 * session. */
void ufwissl_close_connection(ufwissl_session * sess);

/* Set the proxy server to be used for the session. */
/*void ufwissl_session_proxy(ufwissl_session *sess,
		      const char *hostname, unsigned int port);
*/

/* Set a new value for a particular session flag. */
void ufwissl_set_session_flag(ufwissl_session * sess, ufwissl_session_flag flag,
			    int value);

/* Return 0 if the given flag is not set, >0 it is set, or -1 if the
 * flag is not supported. */
int ufwissl_get_session_flag(ufwissl_session * sess, ufwissl_session_flag flag);

/* Bypass the normal name resolution; force the use of specific set of
 * addresses for this session, addrs[0]...addrs[n-1].  The addrs array
 * must remain valid until the session is destroyed. */
void ufwissl_set_addrlist(ufwissl_session * sess,
			const ufwissl_inet_addr ** addrs, size_t n);

/* DEPRECATED: Progress callback. */
typedef void (*ufwissl_progress) (void *userdata, ufwissl_off_t progress,
				ufwissl_off_t total);

/* DEPRECATED API: Set a progress callback for the session; this is
 * deprecated in favour of ufwissl_set_notifier().  The progress callback
 * is invoked for after each block of the request and response body to
 * indicate request and response progress (there is no way to
 * distinguish between the two using this interface alone).
 *
 * NOTE: Use of this interface is mutually exclusive with the use of
 * ufwissl_set_notifier().  A call to ufwissl_set_progress() removes the
 * notifier callback, and vice versa. */
void ufwissl_set_progress(ufwissl_session * sess, ufwissl_progress progress,
			void *userdata);

/* Store an opaque context for the session, 'priv' is returned by a
 * call to ufwissl_session_get_private with the same ID. */
void ufwissl_set_session_private(ufwissl_session * sess, const char *id,
			       void *priv);
void *ufwissl_get_session_private(ufwissl_session * sess, const char *id);

/* Status event type.  NOTE: More event types may be added in
 * subsequent releases, so callers must ignore unknown status types
 * for forwards-compatibility.  */
typedef enum {
	ufwissl_status_lookup = 0,	/* looking up hostname */
	ufwissl_status_connecting,	/* connecting to host */
	ufwissl_status_connected,	/* connected to host */
	ufwissl_status_sending,	/* sending a request body */
	ufwissl_status_recving,	/* receiving a response body */
	ufwissl_status_disconnected	/* disconnected from host */
} ufwissl_session_status;

/* Status event information union; the relevant structure within
 * corresponds to the event type.  WARNING: the size of this union is
 * not limited by ABI constraint; it may be extended with additional
 * members of different size, or existing members may be extended. */
typedef union ufwissl_session_status_info_u {
	struct {		/* ufwissl_status_lookup */
		/* The hostname which is being resolved: */
		const char *hostname;
	} lu;
	struct {		/* ufwissl_status_connecting */
		/* The hostname and network address to which a connection
		 * attempt is being made: */
		const char *hostname;
		const ufwissl_inet_addr *address;
	} ci;
	struct {		/* ufwissl_status_connected, ufwissl_status_disconnected */
		/* The hostname to which a connection has just been
		 * established or closed: */
		const char *hostname;
	} cd;
	struct {		/* ufwissl_status_sending and ufwissl_status_recving */
		/* Request/response body transfer progress; if total == -1, the
		 * total size is unknown; else 0 <= progress <= total:  */
		ufwissl_off_t progress, total;
	} sr;
} ufwissl_session_status_info;

/* Callback invoked to notify a new session status event, given by the
 * 'status' argument.  On invocation, the contents of exactly one of
 * the structures in the info union will be valid, as indicated
 * above. */
typedef void (*ufwissl_notify_status) (void *userdata,
				     ufwissl_session_status status,
				     const ufwissl_session_status_info *
				     info);

/* Set a status notification callback for the session, to report
 * session status events.  Only one notification callback per session
 * can be registered; the most recent of successive calls to this
 * function takes effect. Note that
 *
 * NOTE: Use of this interface is mutually exclusive with the use of
 * ufwissl_set_progress().  A call to ufwissl_set_notifier() removes the
 * progress callback, and vice versa. */
void ufwissl_set_notifier(ufwissl_session * sess, ufwissl_notify_status status,
			void *userdata);

/* Certificate verification failures.
 * The certificate is not yet valid: */
#define UFWISSL_SSL_NOTYETVALID (0x01)
/* The certificate has expired: */
#define UFWISSL_SSL_EXPIRED (0x02)
/* The hostname for which the certificate was issued does not
 * match the hostname of the server; this could mean that the
 * connection is being intercepted: */
#define UFWISSL_SSL_IDMISMATCH (0x04)
/* The certificate authority which signed the server certificate is
 * not trusted: there is no indicatation the server is who they claim
 * to be: */
#define UFWISSL_SSL_UNTRUSTED (0x08)
/* The certificate is invalid */
#define UFWISSL_SSL_INVALID (0x10)
/* The certificate has been revoked */
#define UFWISSL_SSL_REVOKED (0x20)
/* The certificate issuer has not been found in the trust chain */
#define UFWISSL_SSL_SIGNER_NOT_FOUND (0x40)
/* The certificate is not signed by a CA */
#define UFWISSL_SSL_SIGNER_NOT_CA (0x80)



/* The bitmask of known failure bits: if (failures & ~UFWISSL_SSL_FAILMASK)
 * is non-zero, an unrecognized failure is given, and the verification
 * should be failed. */
#define UFWISSL_SSL_FAILMASK (0xff)

#if 0
/* A callback which is used when server certificate verification is
 * needed.  The reasons for verification failure are given in the
 * 'failures' parameter, which is a binary OR of one or more of the
 * above UFWISSL_SSL_* values. failures is guaranteed to be non-zero.  The
 * callback must return zero to accept the certificate: a non-zero
 * return value will fail the SSL negotiation. */
typedef int (*ufwissl_ssl_verify_fn) (void *userdata, int failures,
				    const ufwissl_ssl_certificate * cert);

/* Install a callback to handle server certificate verification.  This
 * is required when the CA certificate is not known for the server
 * certificate, or the server cert has other verification problems. */
void ufwissl_ssl_set_verify(ufwissl_session * sess, ufwissl_ssl_verify_fn fn,
			  void *userdata);
#endif

/* Use the given client certificate for the session.  The client cert
 * MUST be in the decrypted state, otherwise behaviour is undefined.
 * The 'clicert' object is duplicated internally so can be destroyed
 * by the caller.  */
int ufwissl_ssl_set_clicert(ufwissl_session * sess,
			  const ufwissl_ssl_client_cert * clicert);

#if 0
/* Indicate that the certificate 'cert' is trusted; the 'cert' object
 * is duplicated internally so can be destroyed by the caller.  This
 * function has no effect for non-SSL sessions. */
void ufwissl_ssl_trust_cert(ufwissl_session * sess,
			  const ufwissl_ssl_certificate * cert);

/* If the SSL library provided a default set of CA certificates, trust
 * this set of CAs. */
void ufwissl_ssl_trust_default_ca(ufwissl_session * sess);

/* Callback used to load a client certificate on demand.  If dncount
 * is > 0, the 'dnames' array dnames[0] through dnames[dncount-1]
 * gives the list of CA names which the server indicated were
 * acceptable.  The callback should load an appropriate client
 * certificate and then pass it to 'ufwissl_ssl_set_clicert'. */
typedef void (*ufwissl_ssl_provide_fn) (void *userdata, ufwissl_session * sess,
				      const ufwissl_ssl_dname *
				      const *dnames, int dncount);

/* Register a function to be called when the server requests a client
 * certificate. */
void ufwissl_ssl_provide_clicert(ufwissl_session * sess,
			       ufwissl_ssl_provide_fn fn, void *userdata);
#endif

/* Set the timeout (in seconds) used when reading from a socket.  The
 * timeout value must be greater than zero. */
void ufwissl_set_read_timeout(ufwissl_session * sess, int timeout);

/* Set the timeout (in seconds) used when making a connection.  The
 * timeout value must be greater than zero. */
void ufwissl_set_connect_timeout(ufwissl_session * sess, int timeout);

/* Set the error string for the session; takes printf-like format
 * string. */
void ufwissl_set_error(ufwissl_session * sess, const char *format, ...)
ufwissl_attribute((format(printf, 2, 3)));

/* Retrieve the error string for the session */
const char *ufwissl_get_error(ufwissl_session * sess);

/* Set destination hostname / port */
void ufwissl_set_hostinfo(ufwissl_session * sess, const char *hostname,
			unsigned int port);

/* Write to session */
/* Return UFWISSL_OK on success
 * Returns a UFWISSL_SOCK_* on failure */
int ufwissl_write(ufwissl_session * session, const char *buffer, size_t count);

/* Read from session */
/* Return the number of bytes read on success
 * Returns a UFWISSL_SOCK_* on failure */
ssize_t ufwissl_read(ufwissl_session * session, char *buffer, size_t count);

/* Set private key and certificate */
int ufwissl_ssl_set_keypair(ufwissl_session * session, const char *cert_file,
			  const char *key_file);

/* Set private key and certificate */
int ufwissl_ssl_set_pkcs12_keypair(ufwissl_session * session,
				 const char *cert_file,
				 const char *key_file);

/* Indicate that the certificate 'cert' is trusted */
int ufwissl_ssl_trust_cert_file(ufwissl_session * sess, const char *cert_file);

/* Add directory of trusted certificates */
int ufwissl_ssl_trust_dir(ufwissl_session * sess, const char *dir);

ufwissl_ssl_client_cert *ufwissl_ssl_import_keypair(const char *cert_file,
						const char *key_file);

char *ufwissl_get_cert_info(ufwissl_session * sess);
char *ufwissl_get_server_cert_dn(ufwissl_session * sess);
char *ufwissl_get_server_cert_info(ufwissl_session * sess);
int ufwissl_init();

UFWISSL_END_DECLS
#endif				/* UFWISSL_SESSION_H */
