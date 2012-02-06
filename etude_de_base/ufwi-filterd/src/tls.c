/*
 ** Copyright (C) 2002-2008 INL
 ** Written by Eric Leblond <eric@regit.org>
 **            Vincent Deffontaines <vincent@gryzor.com>
 **            Pierre Chifflier <chifflier@inl.fr>
 ** INL http://www.inl.fr/
 **
 ** $Id$
 **
 ** This program is free software; you can redistribute it and/or modify
 ** it under the terms of the GNU General Public License as published by
 ** the Free Software Foundation, version 3 of the License.
 **
 ** This program is distributed in the hope that it will be useful,
 ** but WITHOUT ANY WARRANTY; without even the implied warranty of
 ** MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 ** GNU General Public License for more details.
 **
 ** You should have received a copy of the GNU General Public License
 ** along with this program; if not, write to the Free Software
 ** Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
 */

#include "nufw.h"

#include <ufwibase.h>
#include <ufwissl.h>

#include <sys/socket.h>
#include <sys/un.h>

/* see <sys/un.h> for details - value is hardcoded */
#define UNIX_MAX_PATH 108


/**
 * \file nufw/tls.c
 * \brief Create a TLS connection to NuAuth
 *
 * Create a TLS connection to NuAuth using tls_connect().
 */

/**
 * Check nuauth certification domain name (DN).
 *
 * Returns 1 on error, 0 if the domain name is valid.
 */
#if 0
unsigned int check_nuauth_cert_dn(gnutls_session *tls_session)
{
	/* we check that dn provided in nuauth certificate is valid */
	char dn[128];
	size_t size;
	int ret;

#if 0
	unsigned int algo, bits;
	time_t expiration_time,
	       activation_time;
#endif
	const gnutls_datum *cert_list;
	unsigned int cert_list_size = 0;
	gnutls_x509_crt cert;

	/* This function only works for X.509 certificates.
	*/
	if (gnutls_certificate_type_get(*tls_session) != GNUTLS_CRT_X509)
		return 0;

	cert_list = gnutls_certificate_get_peers(*tls_session, &cert_list_size);
	if (cert_list_size == 0) {
		log_area_printf(DEBUG_AREA_MAIN, DEBUG_LEVEL_WARNING,
				"TLS: cannot get the peer certificate");
		return 1;
	}

	/* we only print information about the first certificate */
	ret = gnutls_x509_crt_init(&cert);
	if (ret != 0) {
		log_area_printf	(DEBUG_AREA_MAIN, DEBUG_LEVEL_WARNING,
				"TLS: cannot init x509 cert: %s",
				gnutls_strerror(ret));
		return 0;
	}

	ret = gnutls_x509_crt_import(cert, &cert_list[0], GNUTLS_X509_FMT_DER);
	if (ret != 0) {
		log_area_printf
			(DEBUG_AREA_MAIN, DEBUG_LEVEL_WARNING,
			 "TLS: cannot import x509 cert: %s",
			 gnutls_strerror(ret));
		return 0;
	}

	/* TODO: verify date */
#if 0
	expiration_time = gnutls_x509_crt_get_expiration_time(cert);
	activation_time = gnutls_x509_crt_get_activation_time(cert);

	/* Extract some of the public key algorithm's parameters */
	algo = gnutls_x509_crt_get_pk_algorithm(cert, &bits);
#endif
	size = sizeof(dn);
	ret = gnutls_x509_crt_get_dn(cert, dn, &size);
	if (ret != 0) {
		log_area_printf (DEBUG_AREA_MAIN, DEBUG_LEVEL_WARNING,
			 "TLS: cannot copy x509 cert name into buffer: %s",
			 gnutls_strerror(ret));
		return 0;
	}
	dn[sizeof(dn)-1] = 0;
	if (strcmp(dn, nuauth_cert_dn)) {
		log_area_printf (DEBUG_AREA_MAIN, DEBUG_LEVEL_WARNING,
			 "TLS: bad certificate DN received from nuauth server: %s",
			 dn);
		return 0;
	}
	return 1;
}
#endif


/**
 * Inialialize key_file and cert_file variables
 */
int init_x509_filenames()
{
#if USE_X509
	if (!key_file) {
		key_file =
			(char *) calloc(strlen(CONFIG_DIR) + strlen(KEYFILE) +
					2, sizeof(char));
		if (!key_file) {
			log_area_printf (DEBUG_AREA_MAIN, DEBUG_LEVEL_WARNING,
						"TLS: cannot allocate the key file");
			return 0;
		}
		strcat(key_file, CONFIG_DIR);
		strcat(key_file, "/");
		strcat(key_file, KEYFILE);
	}
	if (!cert_file) {
		cert_file =
			(char *) calloc(strlen(CONFIG_DIR) + strlen(CERTFILE) +
					2, sizeof(char));
		if (!cert_file) {
			log_area_printf (DEBUG_AREA_MAIN, DEBUG_LEVEL_WARNING,
				"TLS: cannot allocate the cert file");
			return 0;
		}
		strcat(cert_file, CONFIG_DIR);
		strcat(cert_file, "/");
		strcat(cert_file, CERTFILE);
	}
#endif
	return 1;
}

/**
 * Create auth server thread
 */

void tls_connect_unix()
{
	struct sockaddr_un remote;
	socklen_t len;
	int s;
	int ret;
	ufwissl_session* sess;
	int opt;

	log_area_printf(DEBUG_AREA_MAIN, DEBUG_LEVEL_FATAL,
		"Trying to connect to unix socket: %s", authreq_addr);

	s = socket(AF_UNIX, SOCK_STREAM, 0);
	if (s < 0) {
		log_area_printf(DEBUG_AREA_MAIN, DEBUG_LEVEL_DEBUG,
				"Couldn't create socket");
		return;
	}

	remote.sun_family = AF_UNIX;
	strncpy(remote.sun_path, authreq_addr, UNIX_MAX_PATH-1);
	len = strlen(remote.sun_path) + sizeof(remote.sun_family);
	ret = connect(s, (struct sockaddr *)&remote, len);
	if (ret < 0) {
		log_area_printf(DEBUG_AREA_MAIN, DEBUG_LEVEL_DEBUG,
				"Couldn't connect to unix socket");
		return;
	}

	if (buffer_size != 0) {
		opt = buffer_size;
		ret = setsockopt(s, SOL_SOCKET, SO_SNDBUFFORCE, &opt, sizeof(opt));
		if (ret < 0) {
			log_area_printf(DEBUG_AREA_MAIN, DEBUG_LEVEL_DEBUG,
					"Couldn't set send buffer size to unix socket: %s",
					strerror(errno));
			return;
		}
	}

	sess = ufwissl_session_create_with_fd(s, 0 /* verify */);
	/* time *must* be set to 0 (non-blocking calls) to avoid a deadlock
	 * between auth_request_send and authsrv
	 */
	ufwissl_set_read_timeout(sess, 0);

	tls.session = sess;
}

/**
 * Create a TLS connection to NuAuth: create a TCP socket and connect
 * to NuAuth using ::adr_srv.
 *
 * If x509 is enable (USE_X509 equals to 1), create credentials and check
 * NuAuth's one. This function modify the tls variable and in particular
 * set tls.session.
 *
 */
void tls_connect()
{
	int ret;
	ufwissl_session* sess;

	tls.session = NULL;

	if (authreq_addr[0] == '/')
		return tls_connect_unix();

	if (!init_x509_filenames()) {
		log_area_printf(DEBUG_AREA_MAIN, DEBUG_LEVEL_DEBUG,
				"Couldn't malloc for key or cert filename!");
		return;
	}

	sess = ufwissl_session_create(UFWISSL_SSL_CTX_CLIENT);
	if (!sess) {
		log_area_printf(DEBUG_AREA_MAIN, DEBUG_LEVEL_FATAL,
				"Unable to create NuSSL session: %s", ufwissl_get_error(sess));
		return;
	}

	log_area_printf(DEBUG_AREA_MAIN, DEBUG_LEVEL_FATAL, "Loading certificate:%s", cert_file);
	log_area_printf(DEBUG_AREA_MAIN, DEBUG_LEVEL_FATAL, "Loading key:%s", key_file);

	ret = ufwissl_ssl_set_keypair(sess, cert_file, key_file);
	if (ret != UFWISSL_OK) {
		log_area_printf(DEBUG_AREA_MAIN,
				DEBUG_LEVEL_FATAL,
				"TLS: can not set ufwissl certificate or keyfile: %s",
				ufwissl_get_error(sess));
		ufwissl_session_destroy(sess);
		return;
	}

	/* sets the trusted CA file */
	if (ca_file) {
		ret = ufwissl_ssl_trust_cert_file(sess, ca_file);
		if (ret != UFWISSL_OK) {
			log_area_printf(DEBUG_AREA_MAIN,
					DEBUG_LEVEL_FATAL,
					"TLS: can not set ufwissl CA file: %s",
					ufwissl_get_error(sess));
			ufwissl_session_destroy(sess);
			return;
		}
	}

	/* sets the CRL */
	if (crl_file) {
		ret = ufwissl_ssl_set_crl_file(sess, crl_file, ca_file);
		if (ret != UFWISSL_OK) {
			log_area_printf(DEBUG_AREA_MAIN,
					DEBUG_LEVEL_FATAL,
					"TLS: can not set ufwissl CRL file: %s",
					ufwissl_get_error(sess));
			ufwissl_session_destroy(sess);
			return;
		}
	}

	ufwissl_set_hostinfo(sess, authreq_addr, authreq_port);
	ufwissl_set_read_timeout(sess, 0);
	if (!nufw_strict_tls) {
		log_area_printf(DEBUG_AREA_MAIN, DEBUG_LEVEL_WARNING,
				"TLS: disabling certificate verification, as asked.");
		ufwissl_ssl_disable_certificate_check(sess, 1);
	}
	if (!nufw_fqdn_check) {
		log_area_printf(DEBUG_AREA_MAIN, DEBUG_LEVEL_WARNING,
				"TLS: disabling FQDN verification, as asked.");
		ufwissl_set_session_flag(sess, UFWISSL_SESSFLAG_IGNORE_ID_MISMATCH, 1);
	}

	if (ufwissl_open_connection(sess) != UFWISSL_OK) {
		log_area_printf(DEBUG_AREA_MAIN, DEBUG_LEVEL_WARNING,
				"TLS: cannot connect to tls_socket (%s)",
				ufwissl_get_error(sess));
		ufwissl_session_destroy(sess);
		return;
	}

#ifdef XXX
	if (ca_file) {
		if (nuauth_cert_dn) {
			if (!check_nuauth_cert_dn(tls_session)) {
				log_area_printf(DEBUG_AREA_GW, DEBUG_LEVEL_WARNING,
					"TLS: Cannot check the certificate DN");
				return;
			}
		}
	}
#endif

	tls.session = sess;
}
