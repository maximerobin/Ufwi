/*
 ** Copyright (C) 20072009 INL
 ** Written by S.Tricaud <stricaud@inl.fr>
 **            L.Defert <ldefert@inl.fr>
 ** INL http://www.inl.fr/
 **
 ** NuSSL: OpenSSL / GnuTLS layer based on libneon
 */


/*
   SSL/TLS abstraction layer for neon
   Copyright (C) 2003-2006, Joe Orton <joe@manyfish.co.uk>

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

/* ufwissl_ssl.h defines an interface for loading and accessing the
 * properties of SSL certificates. */

#ifndef UFWISSL_SSL_H
#define UFWISSL_SSL_H 1

#include <sys/types.h>

#include "ufwissl_defs.h"

/* UFWISSL_BEGIN_DECLS */

/* A "distinguished name"; a unique name for some entity. */
typedef struct ufwissl_ssl_dname_s ufwissl_ssl_dname;

/* Returns a single-line string representation of a distinguished
 * name, intended to be human-readable (e.g. "Acme Ltd., Norfolk,
 * GB").  Return value is a UTF-8-encoded malloc-allocated string and
 * must be free'd by the caller. */
char *ufwissl_ssl_readable_dname(const ufwissl_ssl_dname * dn);

/* Returns zero if 'dn1' and 'dn2' refer to same name, or non-zero if
 * they are different. */
int ufwissl_ssl_dname_cmp(const ufwissl_ssl_dname * dn1,
			const ufwissl_ssl_dname * dn2);

/* An SSL certificate. */
typedef struct ufwissl_ssl_certificate_s ufwissl_ssl_certificate;

/* Read a certificate from a file in PEM format; returns NULL if the
 * certificate could not be parsed. */
ufwissl_ssl_certificate *ufwissl_ssl_cert_file_read(const char *filename);

/* Write a certificate to a file in PEM format; returns non-zero if
 * the certificate could not be written. */
int ufwissl_ssl_cert_write(const ufwissl_ssl_certificate * cert,
			 const char *filename);

/* Export a certificate to a base64-encoded, NUL-terminated string.
 * The returned string is malloc-allocated and must be free()d by the
 * caller. */
char *ufwissl_ssl_cert_export(const ufwissl_ssl_certificate * cert);

/* Import a certificate from a base64-encoded string as returned by
 * ufwissl_ssl_cert_export(). Returns a certificate object or NULL if
 * 'data' was not valid. */
ufwissl_ssl_certificate *ufwissl_ssl_cert_import(const char *data);

/**
 * Retrieves the “identity” of a certificate; for an SSL server certificate,
 * this will be the hostname for which the certificate was issued.
 * In PKI parlance, the identity is the common name attribute of the
 * distinguished name of the certificate subject.
 * @param cert a ufwissl certificate
 * @see ufwissl_ssl_cert_subject
 * @see ufwissl_ssl_cert_issuer
 * @return the identity of the certificate as UTF-8-encoded string
 * or NULL if none is given.
 * */
const char *ufwissl_ssl_cert_identity(const ufwissl_ssl_certificate * cert);

/* Return the certificate of the entity which signed certificate
 * 'cert'.  Returns NULL if 'cert' is self-signed or the issuer
 * certificate is not available. */
const ufwissl_ssl_certificate *ufwissl_ssl_cert_signedby(const
						     ufwissl_ssl_certificate
						     * cert);

/* Returns the distinguished name of the certificate issuer. */
const ufwissl_ssl_dname *ufwissl_ssl_cert_issuer(const ufwissl_ssl_certificate *
					     cert);

/* Returns the distinguished name of the certificate subject. */
const ufwissl_ssl_dname *ufwissl_ssl_cert_subject(const ufwissl_ssl_certificate *
					      cert);

#define UFWISSL_SSL_DIGESTLEN (60)

/* Calculate the certificate digest ("fingerprint") and format it as a
 * NUL-terminated hex string in 'digest', of the form "aa:bb:...:ff".
 * Returns zero on success or non-zero if there was an internal error
 * whilst calculating the digest.  'digest' must be at least
 * UFWISSL_SSL_DIGESTLEN bytes in length. */
int ufwissl_ssl_cert_digest(const ufwissl_ssl_certificate * cert,
			  char *digest);

/* Copy the validity times for the certificate 'cert' into 'from' and
 * 'until' (either may be NULL).  If the time cannot be represented by
 * a time_t value, then (time_t)-1 will be written. */
void ufwissl_ssl_cert_validity_time(const ufwissl_ssl_certificate * cert,
				  time_t * from, time_t * until);

#define UFWISSL_SSL_VDATELEN (30)
/* Copy the validity times into buffers 'from' and 'until' as
 * NUL-terminated human-readable strings, using RFC 1123-style date
 * formatting (and not localized, so always using English month/week
 * names).  The buffers must be at least UFWISSL_SSL_VDATELEN bytes in
 * length, and either may be NULL. */
void ufwissl_ssl_cert_validity(const ufwissl_ssl_certificate * cert,
			     char *from, char *until);

/* Returns zero if 'c1' and 'c2' refer to the same certificate, or
 * non-zero otherwise. */
int ufwissl_ssl_cert_cmp(const ufwissl_ssl_certificate * c1,
		       const ufwissl_ssl_certificate * c2);

/* Deallocate memory associated with certificate. */
void ufwissl_ssl_cert_free(ufwissl_ssl_certificate * cert);

/* A client certificate (and private key). */
typedef struct ufwissl_ssl_client_cert_s ufwissl_ssl_client_cert;

/* Read a client certificate and private key from a PKCS12 file;
 * returns NULL if the file could not be parsed, or otherwise
 * returning a client certificate object. */
ufwissl_ssl_client_cert *ufwissl_ssl_clicert_read(const char *filename);

/* Returns the "friendly name" given for the client cert, or NULL if
 * none given.  This can be called before or after the client cert has
 * been decrypted.  Returns a NUL-terminated, UTF-8-encoded string. */
const char *ufwissl_ssl_clicert_name(const ufwissl_ssl_client_cert * ccert);

/* Returns non-zero if client cert is encrypted. */
int ufwissl_ssl_clicert_encrypted(const ufwissl_ssl_client_cert * ccert);

/* Decrypt the encrypted client cert using given password.  Returns
 * non-zero on failure, in which case, the function can be called
 * again with a different password.  For a ccert on which _encrypted()
 * returns 0, calling _decrypt results in undefined behaviour. */
int ufwissl_ssl_clicert_decrypt(ufwissl_ssl_client_cert * ccert,
			      const char *password);

/* Return the actual certificate part of the client certificate (never
 * returns NULL). */
const ufwissl_ssl_certificate *ufwissl_ssl_clicert_owner(const
						     ufwissl_ssl_client_cert
						     * ccert);

/* Destroy a client certificate object. */
void ufwissl_ssl_clicert_free(ufwissl_ssl_client_cert * ccert);



/* SSL context object.  The interfaces to manipulate an SSL context
 * are only needed when interfacing directly with ufwissl_socket.h. */
typedef struct ufwissl_ssl_context_s ufwissl_ssl_context;

/* Create an SSL context. */
ufwissl_ssl_context *ufwissl_ssl_context_create(int mode);

/* Client mode: trust the given certificate 'cert' in context 'ctx'. */
int ufwissl_ssl_context_trustcert(ufwissl_ssl_context * ctx,
				const ufwissl_ssl_certificate * cert);

/* Add directory of trusted certificates */
int ufwissl_ssl_context_trustdir(ufwissl_ssl_context * ctx,
				const char *capath);

/* Set the client certificate */
int ufwissl_ssl_context_keypair_from_data(ufwissl_ssl_context * ctx,
					ufwissl_ssl_client_cert * cert);

/* Server mode: use given cert and key (filenames to PEM certificates). */
int ufwissl_ssl_context_keypair(ufwissl_ssl_context * ctx,
			      const char *cert, const char *key);

/* Server mode: Set DH parameters */
int ufwissl_ssl_context_set_dh_bits(ufwissl_ssl_context * ctx,
				  unsigned int dh_bits);

/* Server mode: Set DH parameters */
int ufwissl_ssl_context_set_dh_file(ufwissl_ssl_context * ctx,
				  const char *file);

/* Server mode: set client cert verification options: required is non-zero if
 * a client cert is required, if ca_names is non-NULL it is a filename containing
 * a set of PEM certs from which CA names are sent in the ccert request. */
/*
 * This function has been replaced by:
 * int ufwissl_ssl_context_set_verify(ufwissl_session *session, int required,
 *                                  const char *verify_cas)
 *
int ufwissl_ssl_context_set_verify(ufwissl_ssl_context *ctx, int required,
                              const char *ca_names, const char *verify_cas);
*/

#define UFWISSL_SSL_CTX_SSLv2 (0)
/* Set a flag for the SSL context. */
void ufwissl_ssl_context_set_flag(ufwissl_ssl_context * ctx, int flag,
				int value);

/* Destroy an SSL context. */
void ufwissl_ssl_context_destroy(ufwissl_ssl_context * ctx);

/* UFWISSL_END_DECLS */

#endif
