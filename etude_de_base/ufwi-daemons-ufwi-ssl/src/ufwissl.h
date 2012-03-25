/*
 ** Copyright (C) 2007-2009 INL
 ** Written by S.Tricaud <stricaud@inl.fr>
 **            L.Defert <ldefert@inl.fr>
 **            Pierre Chifflier <chifflier@inl.fr>
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

#ifndef UFWISSL_H
#define UFWISSL_H
#include <stdio.h>
#include <sys/types.h>

#include "ufwissl_constants.h"

#ifdef __cplusplus
extern "C" {
#endif

	struct ufwissl_nession_t;
	typedef struct ufwissl_session_t ufwissl_session;

	typedef void *ufwissl_ptr;

/* Global library initialisation */
	int ufwissl_init();

/* Create a session to the given server, using the given mode.
 * mode can be one of UFWISSL_SSL_CTX_CLIENT, UFWISSL_SSL_CTX_SERVER,
 * or UFWISSL_SSL_CTX_SERVERv2 */
	ufwissl_session *ufwissl_session_create(int mode);

/* Finish an HTTP session */
	void ufwissl_session_destroy(ufwissl_session * sess);

/* Set destination hostname / port */
	void ufwissl_set_hostinfo(ufwissl_session * sess, const char *hostname,
				unsigned int port);

/* Open the connection */
	int ufwissl_open_connection(ufwissl_session * sess);

/* Prematurely force the connection to be closed for the given
 * session. */
	void ufwissl_close_connection(ufwissl_session * sess);

/* Set the timeout (in seconds) used when reading from a socket.  The
 * timeout value must be greater than zero. */
	void ufwissl_set_read_timeout(ufwissl_session * sess, int timeout);

/* Set the timeout (in seconds) used when making a connection.  The
 * timeout value must be greater than zero. */
	void ufwissl_set_connect_timeout(ufwissl_session * sess, int timeout);

/* Retrieve the error string for the session */
	const char *ufwissl_get_error(ufwissl_session * sess);

/* Write to session */
	int ufwissl_write(ufwissl_session * sess, const char *buffer, size_t count);

	ssize_t ufwissl_read_available(ufwissl_session * sess);

/* Read from session */
/* returns the number of octets read on success */
/* returns a UFWISSL_SOCK_* error on failure */
	ssize_t ufwissl_read(ufwissl_session * sess, char *buffer,
			   size_t count);

/* Set private key and certificate */
	int ufwissl_ssl_set_keypair(ufwissl_session * sess,
				  const char *cert_file,
				  const char *key_file);

/* Set private key and certificate */
	int ufwissl_ssl_set_pkcs12_keypair(ufwissl_session * sess,
					 const char *cert_file,
					 const char *key_file);

/* Indicate that the certificate 'cert' is trusted */
	int ufwissl_ssl_trust_cert_file(ufwissl_session * sess,
				      const char *cert_file);

/* Add directory of trusted certificates */
	int ufwissl_ssl_trust_dir(ufwissl_session * sess,
				      const char *dir);

/* TODO: factorize those functions */
/* Returns a string containing informations about the certificate */
	char *ufwissl_get_cert_info(ufwissl_session * sess);

/* Returns a string containing informations about the peer certificate */
	char *ufwissl_get_server_cert_info(ufwissl_session * sess);

/* Returns a string containing informations about the peer certificate */
	char *ufwissl_get_server_cert_dn(ufwissl_session * sess);

/* Returns a string containing informations about the peer certificate */
	int ufwissl_get_peer_dn(ufwissl_session * sess, char *buf,
				size_t * buf_size);

/* Server related functions */
/* Create session server from sock fd */
	ufwissl_session *ufwissl_session_create_with_fd(int fd, int verify);

	ufwissl_session *ufwissl_session_accept(ufwissl_session * srv_sess);

	int ufwissl_session_handshake(ufwissl_session * client_sess,
				    ufwissl_session * srv_sess);

	int ufwissl_session_get_fd(ufwissl_session * sess);

/* Set list of allowed ciphers for TLS negotiation */
	void ufwissl_session_set_ciphers(ufwissl_session * sess, const char *cipher_list);

	int ufwissl_session_get_cipher(ufwissl_session * sess, char *buf, size_t bufsz);

	int ufwissl_session_getpeer(ufwissl_session * sess,
				  struct sockaddr *addr,
				  socklen_t * addrlen);

	int ufwissl_session_set_dh_bits(ufwissl_session * sess,
				      unsigned int dh_bits);

	int ufwissl_session_set_dh_file(ufwissl_session * sess,
				      const char *filename);

	int ufwissl_ssl_set_crl_file(ufwissl_session * sess, const char *crl_file, const char *ca_file);

	/* This function accepts several certificates in the CA file */
	int ufwissl_ssl_set_ca_file(ufwissl_session *sess, const char *cafile);

	void ufwissl_ssl_disable_certificate_check(ufwissl_session * sess, int is_disabled);

	/* Set a new value for a particular session flag. */
	void ufwissl_set_session_flag(ufwissl_session * sess,
		ufwissl_session_flag flag,
		int value);

	int ufwissl_get_session_flag(ufwissl_session * sess,
		ufwissl_session_flag flag);

	void *ufwissl_get_ctx(ufwissl_session * sess);

	void *ufwissl_get_socket(ufwissl_session * sess);

#define UFWISSL_VALID_REQ_TYPE(n) (n >= UFWISSL_CERT_IGNORE && n <= UFWISSL_CERT_REQUIRE)

	/* local check of certificate against CA and CRL (optional) */
	int ufwissl_local_check_certificate(const char *cert,
		const char *ca_cert,
		const char *ca_path,
		const char *crl,
		char *ret_message,
		size_t message_sz);

#ifdef __cplusplus
}
#endif
#endif				/* UFWISSL_H */
