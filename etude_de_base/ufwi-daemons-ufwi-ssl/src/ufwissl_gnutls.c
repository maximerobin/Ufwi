/*
 ** Copyright (C) 2009 INL
 ** Written by S.Tricaud <stricaud@inl.fr>
 **            L.Defert <ldefert@inl.fr>
 **            Pierre Chifflier <p.chifflier@inl.fr>
 ** INL http://www.inl.fr/
 **
 ** NuSSL: OpenSSL / GnuTLS layer based on libneon
 */


/*
   neon SSL/TLS support using GNU TLS
   Copyright (C) 2007, Joe Orton <joe@manyfish.co.uk>
   Copyright (C) 2004, Aleix Conchillo Flaque <aleix@member.fsf.org>

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

#include "config.h"

#ifdef HAVE_GNUTLS

#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/types.h>

#ifdef HAVE_STRING_H
#include <string.h>
#endif

#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <errno.h>

#include <gnutls/gnutls.h>
#include <gnutls/pkcs12.h>

#ifdef HAVE_ICONV
#include <iconv.h>
#endif

#include "ufwissl_privssl.h"
#include "ufwissl_ssl_common.h"

#ifdef UFWISSL_HAVE_TS_SSL
#include <errno.h>
#include <pthread.h>
#include <gcrypt.h>
GCRY_THREAD_OPTION_PTHREAD_IMPL;

#endif

#include <fcntl.h>




#include "ufwissl_ssl.h"
#include "ufwissl_string.h"
#include "ufwissl_session.h"
#include "ufwissl_internal.h"

#include "ufwissl_private.h"
#include "ufwissl_privssl.h"
#include "ufwissl_utils.h"

int read_to_datum(const char *filename, gnutls_datum * datum);

ufwissl_ssl_certificate *ufwissl_ssl_cert_read(const char *filename);

/* Returns the highest used index in subject (or issuer) DN of
 * certificate CERT for OID, or -1 if no RDNs are present in the DN
 * using that OID. */
static int oid_find_highest_index(gnutls_x509_crt cert, int subject,
				  const char *oid)
{
	int ret, idx = -1;

	do {
		size_t len = 0;

		if (subject)
			ret = gnutls_x509_crt_get_dn_by_oid(cert, oid, ++idx,
							    0, NULL, &len);
		else
			ret = gnutls_x509_crt_get_issuer_dn_by_oid(cert, oid,
								   ++idx, 0,
								   NULL,
								   &len);
	} while (ret == GNUTLS_E_SHORT_MEMORY_BUFFER);

	return idx - 1;
}

#ifdef HAVE_GNUTLS_X509_DN_GET_RDN_AVA
/* New-style RDN handling introduced in GnuTLS 1.7.x. */

#ifdef HAVE_ICONV
static void convert_dirstring(ufwissl_buffer * buf, const char *charset,
			      gnutls_datum * data)
{
	iconv_t id = iconv_open("UTF-8", charset);
	size_t inlen = data->size, outlen = buf->length - buf->used;
	char *inbuf = (char *) data->data;
	char *outbuf = buf->data + buf->used - 1;

	if (id == (iconv_t) - 1) {
		char err[128], err2[128];

		ufwissl_snprintf(err, sizeof err, "[unprintable in %s: %s]",
			       charset, ufwissl_strerror(errno, err2,
						       sizeof err2));
		ufwissl_buffer_zappend(buf, err);
		return;
	}

	ufwissl_buffer_grow(buf, buf->used + 64);

	while (inlen && outlen
	       && iconv(id, &inbuf, &inlen, &outbuf, &outlen) == 0);

	iconv_close(id);
	buf->used += buf->length - buf->used - outlen;
	buf->data[buf->used - 1] = '\0';
}
#endif

/* From section 11.13 of the Dubuisson ASN.1 bible: */
#define TAG_UTF8 (12)
#define TAG_PRINTABLE (19)
#define TAG_T61 (20)
#define TAG_IA5 (22)
#define TAG_VISIBLE (26)
#define TAG_UNIVERSAL (28)
#define TAG_BMP (30)

static void append_dirstring(ufwissl_buffer * buf, gnutls_datum * data,
			     unsigned long tag)
{
	switch (tag) {
	case TAG_UTF8:
	case TAG_IA5:
	case TAG_PRINTABLE:
	case TAG_VISIBLE:
		ufwissl_buffer_append(buf, (char *) data->data, data->size);
		break;
#ifdef HAVE_ICONV
	case TAG_T61:
		convert_dirstring(buf, "ISO-8859-1", data);
		break;
	case TAG_BMP:
		convert_dirstring(buf, "UCS-2BE", data);
		break;
#endif
	default:{
			char tmp[128];
			ufwissl_snprintf(tmp, sizeof tmp,
				       _("[unprintable:#%lu]"), tag);
			ufwissl_buffer_zappend(buf, tmp);
		}
		break;
	}
}

/* OIDs to not include in readable DNs by default: */
#define OID_emailAddress "1.2.840.113549.1.9.1"
#define OID_commonName "2.5.4.3"

#define CMPOID(a,o) ((a)->oid.size == sizeof(o)                        \
		&& memcmp((a)->oid.data, o, strlen(o)) == 0)

char *ufwissl_ssl_readable_dname(const ufwissl_ssl_dname * name)
{
	gnutls_x509_dn_t dn;
	int ret, rdn = 0, flag = 0;
	ufwissl_buffer *buf;
	gnutls_x509_ava_st val;

	if (name->subject)
		ret = gnutls_x509_crt_get_subject(name->cert, &dn);
	else
		ret = gnutls_x509_crt_get_issuer(name->cert, &dn);

	if (ret)
		return ufwissl_strdup(_("[unprintable]"));

	buf = ufwissl_buffer_create();

	/* Find the highest rdn... */
	while (gnutls_x509_dn_get_rdn_ava(dn, rdn++, 0, &val) == 0);

	/* ..then iterate back to the first: */
	while (--rdn >= 0) {
		int ava = 0;

		/* Iterate through all AVAs for multivalued AVAs; better than
		 * ufwissl_openssl can do! */
		do {
			ret = gnutls_x509_dn_get_rdn_ava(dn, rdn, ava, &val);

			/* If the *only* attribute to append is the common name or
			 * email address, use it; otherwise skip those
			 * attributes. */
			if (ret == 0 && val.value.size > 0
			    && ((!CMPOID(&val, OID_emailAddress)
				 && !CMPOID(&val, OID_commonName))
				|| (buf->used == 1 && rdn == 0))) {
				flag = 1;
				if (buf->used > 1)
					ufwissl_buffer_append(buf, ", ", 2);

				append_dirstring(buf, &val.value,
						 val.value_tag);
			}

			ava++;
		} while (ret == 0);
	}

	return ufwissl_buffer_finish(buf);
}

#else				/* !HAVE_GNUTLS_X509_DN_GET_RDN_AVA */

/* Appends the value of RDN with given oid from certitifcate x5
 * subject (if subject is non-zero), or issuer DN to buffer 'buf': */
static void append_rdn(ufwissl_buffer * buf, gnutls_x509_crt x5, int subject,
		       const char *oid)
{
	int idx, top, ret;
	char rdn[50];

	top = oid_find_highest_index(x5, subject, oid);

	for (idx = top; idx >= 0; idx--) {
		size_t rdnlen = sizeof rdn;

		if (subject)
			ret = gnutls_x509_crt_get_dn_by_oid(x5, oid, idx, 0,
							    rdn, &rdnlen);
		else
			ret = gnutls_x509_crt_get_issuer_dn_by_oid(x5, oid,
								   idx, 0,
								   rdn,
								   &rdnlen);

		if (ret < 0)
			return;

		if (buf->used > 1) {
			ufwissl_buffer_append(buf, ", ", 2);
		}

		ufwissl_buffer_append(buf, rdn, rdnlen);
	}
}

char *ufwissl_ssl_readable_dname(const ufwissl_ssl_dname * name)
{
	ufwissl_buffer *buf = ufwissl_buffer_create();
	int ret, idx = 0;

	do {
		char oid[32] = { 0 };
		size_t oidlen = sizeof oid;

		ret = name->subject
		    ? gnutls_x509_crt_get_dn_oid(name->cert, idx, oid,
						 &oidlen)
		    : gnutls_x509_crt_get_issuer_dn_oid(name->cert, idx,
							oid, &oidlen);

		if (ret == 0) {
			append_rdn(buf, name->cert, name->subject, oid);
			idx++;
		}
	} while (ret != GNUTLS_E_REQUESTED_DATA_NOT_AVAILABLE);

	return ufwissl_buffer_finish(buf);
}
#endif				/* HAVE_GNUTLS_X509_DN_GET_RDN_AVA */

int ufwissl_ssl_dname_cmp(const ufwissl_ssl_dname * dn1,
			const ufwissl_ssl_dname * dn2)
{
	char c1[1024], c2[1024];
	size_t s1 = sizeof c1, s2 = sizeof c2;
	int ret;

	if (dn1->subject)
		ret = gnutls_x509_crt_get_dn(dn1->cert, c1, &s1);
	else
		ret = gnutls_x509_crt_get_issuer_dn(dn1->cert, c1, &s1);
	if (ret)
		return 1;

	if (dn2->subject)
		ret = gnutls_x509_crt_get_dn(dn2->cert, c2, &s2);
	else
		ret = gnutls_x509_crt_get_issuer_dn(dn2->cert, c2, &s2);
	if (ret)
		return -1;

	if (s1 != s2)
		return s2 - s1;

	return memcmp(c1, c2, s1);
}

void ufwissl_ssl_clicert_free(ufwissl_ssl_client_cert * cc)
{
	if (cc->p12)
		gnutls_pkcs12_deinit(cc->p12);
	if (cc->decrypted) {
		if (cc->cert.identity)
			ufwissl_free(cc->cert.identity);
		if (cc->pkey)
			gnutls_x509_privkey_deinit(cc->pkey);
		if (cc->cert.subject)
			gnutls_x509_crt_deinit(cc->cert.subject);
	}
	if (cc->friendly_name)
		ufwissl_free(cc->friendly_name);
	ufwissl_free(cc);
}

void ufwissl_ssl_cert_validity_time(const ufwissl_ssl_certificate * cert,
				  time_t * from, time_t * until)
{
	if (from) {
		*from = gnutls_x509_crt_get_activation_time(cert->subject);
	}
	if (until) {
		*until =
		    gnutls_x509_crt_get_expiration_time(cert->subject);
	}
}

/* Check certificate identity.  Returns zero if identity matches or could
 * not be checked; 1 if identity does not match, or <0 if the certificate had
 * no identity.
 * if hostname is not NULL, store certificate identity
 */
static int check_identity(const char *expected_hostname, gnutls_x509_crt cert, char **hostname)
{
	char name[255];
	int ret;
	size_t len;

	len = sizeof(name);
	ret = gnutls_x509_crt_get_dn_by_oid(cert, GNUTLS_OID_X520_COMMON_NAME,
		0, /* the first and only one */
		0,
		name,
		&len);
	if (ret) {
		if (expected_hostname != NULL)
			UFWISSL_DEBUG(UFWISSL_DBG_SSL,
				"TLS: error fetching CN from cert: %s",
				gnutls_strerror(ret));
				return -1;
	}

	if (hostname) {
		*hostname = ufwissl_strdup(name);
	}

	/* we can't check the identifity .. */
	if (!expected_hostname)
		return 0;

	/* This function will check if the given certificate's subject matches the
	 * given hostname. This is a basic implementation of the matching described
	 * in RFC2818 (HTTPS), which takes into account wildcards, and the subject
	 * alternative name PKIX extension. Returns non zero on success, and zero on
	 * failure. */
	ret = gnutls_x509_crt_check_hostname(cert, expected_hostname);
	if (!ret) {
		UFWISSL_DEBUG(UFWISSL_DBG_SSL,
			"SSL: certificate subject name (%s) does not match target host name '%s'\n",
			name, expected_hostname);
			return 1;
	}


	return 0;
}

/* Populate an ufwissl_ssl_certificate structure from an X509 object. */
static ufwissl_ssl_certificate *populate_cert(ufwissl_ssl_certificate * cert,
					    gnutls_x509_crt x5)
{
	cert->subj_dn.cert = x5;
	cert->subj_dn.subject = 1;
	cert->issuer_dn.cert = x5;
	cert->issuer_dn.subject = 0;
	cert->issuer = NULL;
	cert->subject = x5;
	cert->identity = NULL;
	check_identity(NULL, x5, &cert->identity);	/* TODO: return the error of check_identity ... */
	return cert;
}

/* Returns a copy certificate of certificate SRC. */
static gnutls_x509_crt x509_crt_copy(gnutls_x509_crt src)
{
	int ret;
	size_t size = 0;
	gnutls_datum tmp;
	gnutls_x509_crt dest;

	if (gnutls_x509_crt_init(&dest) != 0) {
		return NULL;
	}

	if (gnutls_x509_crt_export(src, GNUTLS_X509_FMT_DER, NULL, &size)
	    != GNUTLS_E_SHORT_MEMORY_BUFFER) {
		gnutls_x509_crt_deinit(dest);
		return NULL;
	}

	tmp.data = ufwissl_malloc(size);
	ret =
	    gnutls_x509_crt_export(src, GNUTLS_X509_FMT_DER, tmp.data,
				   &size);
	if (ret == 0) {
		tmp.size = size;
		ret = gnutls_x509_crt_import(dest, &tmp,
					     GNUTLS_X509_FMT_DER);
	}

	if (ret) {
		gnutls_x509_crt_deinit(dest);
		dest = NULL;
	}

	ufwissl_free(tmp.data);
	return dest;
}

/* Duplicate a client certificate, which must be in the decrypted state. */
static ufwissl_ssl_client_cert *dup_client_cert(const ufwissl_ssl_client_cert *
					      cc)
{
	int ret;
	ufwissl_ssl_client_cert *newcc = ufwissl_calloc(sizeof *newcc);

	newcc->decrypted = 1;

	ret = gnutls_x509_privkey_init(&newcc->pkey);
	if (ret != 0)
		goto dup_error;

	ret = gnutls_x509_privkey_cpy(newcc->pkey, cc->pkey);
	if (ret != 0)
		goto dup_error;

	newcc->cert.subject = x509_crt_copy(cc->cert.subject);
	if (!newcc->cert.subject)
		goto dup_error;

	if (cc->friendly_name)
		newcc->friendly_name = ufwissl_strdup(cc->friendly_name);

	populate_cert(&newcc->cert, newcc->cert.subject);
	return newcc;

dup_error:
	if (newcc->pkey)
		gnutls_x509_privkey_deinit(newcc->pkey);
	if (newcc->cert.subject)
		gnutls_x509_crt_deinit(newcc->cert.subject);
	ufwissl_free(newcc);
	return NULL;
}

#if 0				/* Use gnutls function, no callback needed */
/* Callback invoked when the SSL server requests a client certificate.  */
static int provide_client_cert(gnutls_session session,
			       const gnutls_datum * req_ca_rdn, int nreqs,
			       const gnutls_pk_algorithm * sign_algos,
			       int sign_algos_length, gnutls_retr_st * st)
{
	ufwissl_session *sess = gnutls_session_get_ptr(session);

	if (!sess) {
		return -1;
	}

	if (!sess->my_cert && sess->ssl_provide_fn) {
		/* The dname array cannot be converted without better dname
		 * support from GNUTLS. */
		sess->ssl_provide_fn(sess->ssl_provide_ud, sess, NULL, 0);
	}

	UFWISSL_DEBUG(UFWISSL_DBG_SSL, "In client cert provider callback.\n");

	if (sess->my_cert) {
		gnutls_certificate_type type =
		    gnutls_certificate_type_get(session);
		if (type == GNUTLS_CRT_X509) {
			UFWISSL_DEBUG(UFWISSL_DBG_SSL,
				    "Supplying client certificate.\n");

			st->type = type;
			st->ncerts = 1;
			st->cert.x509 = &sess->my_cert->cert.subject;
			st->key.x509 = sess->my_cert->pkey;

			/* tell GNU TLS not to deallocate the certs. */
			st->deinit_all = 0;
		} else {
			return -1;
		}
	} else {
		UFWISSL_DEBUG(UFWISSL_DBG_SSL,
			    "No client certificate supplied.\n");
	}

	return 0;
}
#endif

int ufwissl_ssl_set_clicert(ufwissl_session * sess,
			  const ufwissl_ssl_client_cert * cc)
{
	sess->my_cert = dup_client_cert(cc);
	if (!sess->my_cert)
		return UFWISSL_ERROR;

	return ufwissl_ssl_context_keypair_from_data(sess->ssl_context,
						   sess->my_cert);
}

/* Return the certificate chain sent by the peer, or NULL on error. */
static ufwissl_ssl_certificate *make_peers_chain(gnutls_session sock)
{
	ufwissl_ssl_certificate *current = NULL, *top = NULL;
	const gnutls_datum *certs;
	unsigned int n, count;

	certs = gnutls_certificate_get_peers(sock, &count);
	if (!certs) {
		return NULL;
	}

	for (n = 0; n < count; n++) {
		ufwissl_ssl_certificate *cert;
		gnutls_x509_crt x5;

		if (gnutls_x509_crt_init(&x5) ||
		    gnutls_x509_crt_import(x5, &certs[n],
					   GNUTLS_X509_FMT_DER)) {
			ufwissl_ssl_cert_free(top);
			return NULL;
		}

		cert = populate_cert(ufwissl_malloc(sizeof *cert), x5);

		if (top == NULL) {
			current = top = cert;
		} else {
			current->issuer = cert;
			current = cert;
		}
	}

	return top;
}

/* Verifies an SSL server certificate. */
static int check_certificate(ufwissl_session * sess, gnutls_session sock,
			     ufwissl_ssl_certificate * chain)
{
	time_t before, after, now = time(NULL);
	int ret, failures = 0;
	unsigned int status;
/*     ufwissl_uri server; */

	before = gnutls_x509_crt_get_activation_time(chain->subject);
	after = gnutls_x509_crt_get_expiration_time(chain->subject);

	if (now < before)
		failures |= UFWISSL_SSL_NOTYETVALID;
	else if (now > after)
		failures |= UFWISSL_SSL_EXPIRED;

	ret = check_identity(sess->server.hostname, chain->subject, NULL);
	if (ret < 0) {
		ufwissl_set_error(sess,
				_("Server certificate was missing commonName "
				 "attribute in subject name"));
		return UFWISSL_ERROR;
	} else if (ret > 0) {
		if (sess->flags[UFWISSL_SESSFLAG_IGNORE_ID_MISMATCH] == 0)
			failures |= UFWISSL_SSL_IDMISMATCH;
	}

	ret = gnutls_certificate_verify_peers2(sock, &status);
	if (ret < 0) {
		UFWISSL_DEBUG(UFWISSL_DBG_SSL,
			    "Certificate verification failed: %s\n",
			    gnutls_strerror(ret));
		failures |= UFWISSL_SSL_UNTRUSTED;
	}
	if (status || failures) {
		UFWISSL_DEBUG(UFWISSL_DBG_SSL,
			    "Certificate verification failed: ");
		if (status & GNUTLS_CERT_INVALID) {
			UFWISSL_DEBUG(UFWISSL_DBG_SSL, "invalid, ");
			failures |= UFWISSL_SSL_INVALID;
		}
		if (status & GNUTLS_CERT_REVOKED) {
			UFWISSL_DEBUG(UFWISSL_DBG_SSL, "revoked, ");
			failures |= UFWISSL_SSL_REVOKED;
		}
		if (status & GNUTLS_CERT_SIGNER_NOT_FOUND) {
			UFWISSL_DEBUG(UFWISSL_DBG_SSL, "signer not found, ");
			failures |= UFWISSL_SSL_SIGNER_NOT_FOUND;
		}
		if (status & GNUTLS_CERT_SIGNER_NOT_CA) {
			UFWISSL_DEBUG(UFWISSL_DBG_SSL, "signer not a CA, ");
			failures |= UFWISSL_SSL_SIGNER_NOT_CA;
		}
		if (failures & UFWISSL_SSL_UNTRUSTED) {
			UFWISSL_DEBUG(UFWISSL_DBG_SSL, "untrusted, ");
		}
		if (failures & UFWISSL_SSL_EXPIRED) {
			UFWISSL_DEBUG(UFWISSL_DBG_SSL, "expired, ");
		}
		if (failures & UFWISSL_SSL_NOTYETVALID) {
			UFWISSL_DEBUG(UFWISSL_DBG_SSL, "not yet valid, ");
		}
		if (failures & UFWISSL_SSL_IDMISMATCH) {
			UFWISSL_DEBUG(UFWISSL_DBG_SSL, "FQDN mismatch, ");
		}
		failures |= UFWISSL_SSL_UNTRUSTED;
	}

	UFWISSL_DEBUG(UFWISSL_DBG_SSL, "\nFailures = %d\n", failures);

	if (failures == 0) {
		ret = UFWISSL_OK;
	} else {
		ufwissl__ssl_set_verify_err(sess, failures);
		ret = UFWISSL_ERROR;
#if 0
		if (sess->ssl_verify_fn
		    && sess->ssl_verify_fn(sess->ssl_verify_ud, failures,
					   chain) == 0)
			ret = UFWISSL_OK;
#endif
	}
	return ret;
}

int ufwissl__ssl_post_handshake(ufwissl_session * sess)
{
	ufwissl_ssl_certificate *chain;
	gnutls_session sock = ufwissl__sock_sslsock(sess->socket);

	if (!sess->check_peer_cert)
		return UFWISSL_OK;

	chain = make_peers_chain(sock);
	if (chain == NULL) {
		ufwissl_set_error(sess, _("Peer did not send certificate chain"));
		if (sess->ssl_context->verify < 2) {
			/* certificates are not mandatory, so continue */
			return UFWISSL_OK;
		}
		return UFWISSL_ERROR;
	}

	if (sess->peer_cert
	    && ufwissl_ssl_cert_cmp(sess->peer_cert, chain) == 0) {
		/* Same cert as last time; presume OK.  This is not optimal as
		 * make_peers_chain() has already gone through and done the
		 * expensive DER parsing stuff for the whole chain by now. */
		ufwissl_ssl_cert_free(chain);
		return UFWISSL_OK;
	}

	if (check_certificate(sess, sock, chain) != UFWISSL_OK &&
	    sess->check_peer_cert != 0) {
		ufwissl_ssl_cert_free(chain);
		ufwissl_set_error(sess, "Certificate verification failed");
		return UFWISSL_ERROR;
	}

	sess->peer_cert = chain;
	return UFWISSL_OK;
}

/* Negotiate an SSL connection. */
int ufwissl__negotiate_ssl(ufwissl_session * sess)
{
	ufwissl_ssl_context *const ctx = sess->ssl_context;

	UFWISSL_DEBUG(UFWISSL_DBG_SSL, "Negotiating SSL connection.\n");

	/* Pass through the hostname if SNI is enabled. */
	ctx->hostname =
	    sess->flags[UFWISSL_SESSFLAG_TLS_SNI] ? sess->server.
	    hostname : NULL;

	if (ufwissl_sock_connect_ssl(sess->socket, ctx, sess)) {
		ufwissl_set_error(sess, _("SSL negotiation failed: %s"),
				ufwissl_sock_error(sess->socket));
		return UFWISSL_ERROR;
	}

	return ufwissl__ssl_post_handshake(sess);
}

const ufwissl_ssl_dname *ufwissl_ssl_cert_issuer(const ufwissl_ssl_certificate *
					     cert)
{
	return &cert->issuer_dn;
}

const ufwissl_ssl_dname *ufwissl_ssl_cert_subject(const ufwissl_ssl_certificate *
					      cert)
{
	return &cert->subj_dn;
}

const ufwissl_ssl_certificate *ufwissl_ssl_cert_signedby(const
						     ufwissl_ssl_certificate
						     * cert)
{
	return cert->issuer;
}

const char *ufwissl_ssl_cert_identity(const ufwissl_ssl_certificate * cert)
{
	return cert->identity;
}

static int check_crl_validity(ufwissl_session * sess, const char *crl_file, const char *ca_file)
{
	gnutls_datum_t datum_crl;
	gnutls_datum_t datum_ca;
	gnutls_x509_crt_t ca;
	gnutls_x509_crl_t crl;
	time_t t, now;
	int return_value;
	char buffer[256];
	size_t s;
	int ret;

	datum_ca.data = NULL;
	datum_crl.data = NULL;

	UFWISSL_DEBUG(UFWISSL_DBG_SSL, "Checking CRL file %s against %s", crl_file, ca_file);
	if (!ca_file || !crl_file)
		return -1;

	/* read CRL and CA */
	ret = read_to_datum(crl_file, &datum_crl);
	if (ret != 0)
		return -1;

	ret = read_to_datum(ca_file, &datum_ca);
	if (ret != 0) {
		ufwissl_free(datum_crl.data);
		return -1;
	}

	gnutls_x509_crt_init(&ca);
	gnutls_x509_crl_init(&crl);

	ret = gnutls_x509_crl_import(crl, &datum_crl, GNUTLS_X509_FMT_PEM);
	if (ret) {
		ufwissl_set_error(sess,_("TLS: Could not import CRL data\n"));
		ufwissl_free(datum_ca.data);
		ufwissl_free(datum_crl.data);
		return -1;
	}

	ret = gnutls_x509_crt_import(ca, &datum_ca, GNUTLS_X509_FMT_PEM);
	if (ret) {
		ufwissl_set_error(sess,_("TLS: Could not import CA data\n"));
		gnutls_free(datum_ca.data);
		gnutls_free(datum_crl.data);
		return -1;
	}


	/* debug stuff */
	s = sizeof(buffer);
	ret = gnutls_x509_crl_get_issuer_dn(crl, buffer, &s);
	UFWISSL_DEBUG(UFWISSL_DBG_SSL, "TLS: CRL issuer DN: %s.\n", buffer);

	/* Check if CRL was signed by configured CA */
	return_value = 0;
	ret = gnutls_x509_crl_check_issuer (crl, ca);
	if (ret != 1) {
		ufwissl_set_error(sess,_("TLS: CRL issuer is NOT the configured certificate authority\n"));
		return_value--;
	}

	/* Check if CRL has expired */
	now = time(NULL);
	t = gnutls_x509_crl_get_next_update (crl);
	/* This field is optional in a CRL */
	if (t != (time_t)-1 ) {
		if (now > t) {
			/* XXX how can we send a warning to caller  from ufwissl ? */
			//ufwissl_set_error(sess,_("TLS: CRL has expired and should be re-issued\n"));
			UFWISSL_DEBUG(UFWISSL_DBG_SSL, _("TLS: CRL has expired and should be re-issued\n"));
			return_value--;
		}
	}

	gnutls_x509_crt_deinit(ca);
	gnutls_x509_crl_deinit(crl);
	ufwissl_free(datum_ca.data);
	ufwissl_free(datum_crl.data);

	return return_value;

}

int ufwissl_ssl_set_crl_file(ufwissl_session * sess, const char *crl_file, const char *ca_file)
{
	int ret;

	if (check_crl_validity(sess, crl_file, ca_file) != 0) {
		return UFWISSL_FAILED;
	}

	/* this function returns the number of CRLs processed
	 * or a negative value on error.
	 */
	ret = gnutls_certificate_set_x509_crl_file(sess->ssl_context->cred,
						  crl_file,
						  GNUTLS_X509_FMT_PEM);

	return (ret > 0) ? UFWISSL_OK : UFWISSL_FAILED;
}

int ufwissl_ssl_set_ca_file(ufwissl_session *sess, const char *cafile)
{
	int ret;
	ufwissl_ssl_certificate *ca;

	ca = ufwissl_ssl_cert_read(cafile);
	if (ca == NULL) {
		ufwissl_set_error(sess,
				_("Unable to load trust certificate"));
		return UFWISSL_ERROR;
	}

	ret = ufwissl_ssl_context_trustcert(sess->ssl_context, ca);

	if (ret == UFWISSL_OK)
		sess->check_peer_cert = 1;

	return ret;
}

/* Read the contents of file FILENAME into *DATUM. */
int read_to_datum(const char *filename, gnutls_datum * datum)
{
	FILE *f = fopen(filename, "r");
	ufwissl_buffer *buf;
	char tmp[4192];
	size_t len;

	if (!f) {
		return -1;
	}

	buf = ufwissl_buffer_ncreate(8192);
	while ((len = fread(tmp, 1, sizeof tmp, f)) > 0) {
		ufwissl_buffer_append(buf, tmp, len);
	}

	if (!feof(f)) {
		ufwissl_buffer_destroy(buf);
		return -1;
	}

	datum->size = ufwissl_buffer_size(buf);
	datum->data = (unsigned char *) ufwissl_buffer_finish(buf);
	return 0;
}

/* Parses a PKCS#12 structure and loads the certificate, private key
 * and friendly name if possible.  Returns zero on success, non-zero
 * on error. */
static int pkcs12_parse(gnutls_pkcs12 p12, gnutls_x509_privkey * pkey,
			gnutls_x509_crt * x5, char **friendly_name,
			const char *password)
{
	gnutls_pkcs12_bag bag = NULL;
	int i, j, ret = 0;

	for (i = 0; ret == 0; ++i) {
		if (bag)
			gnutls_pkcs12_bag_deinit(bag);

		ret = gnutls_pkcs12_bag_init(&bag);
		if (ret < 0)
			continue;

		ret = gnutls_pkcs12_get_bag(p12, i, bag);
		if (ret < 0)
			continue;

		gnutls_pkcs12_bag_decrypt(bag, password);

		for (j = 0;
		     ret == 0 && j < gnutls_pkcs12_bag_get_count(bag);
		     ++j) {
			gnutls_pkcs12_bag_type type;
			gnutls_datum data;

			if (friendly_name && *friendly_name == NULL) {
				char *name = NULL;
				gnutls_pkcs12_bag_get_friendly_name(bag, j,
								    &name);
				if (name) {
					if (name[0] == '.')
						name++;	/* weird GnuTLS bug? */
					*friendly_name =
					    ufwissl_strdup(name);
				}
			}

			type = gnutls_pkcs12_bag_get_type(bag, j);
			switch (type) {
			case GNUTLS_BAG_PKCS8_KEY:
			case GNUTLS_BAG_PKCS8_ENCRYPTED_KEY:
				gnutls_x509_privkey_init(pkey);

				ret =
				    gnutls_pkcs12_bag_get_data(bag, j,
							       &data);
				if (ret < 0)
					continue;

				ret =
				    gnutls_x509_privkey_import_pkcs8(*pkey,
								     &data,
								     GNUTLS_X509_FMT_DER,
								     password,
								     0);
				if (ret < 0)
					continue;
				break;
			case GNUTLS_BAG_CERTIFICATE:
				gnutls_x509_crt_init(x5);

				ret =
				    gnutls_pkcs12_bag_get_data(bag, j,
							       &data);
				if (ret < 0)
					continue;

				ret =
				    gnutls_x509_crt_import(*x5, &data,
							   GNUTLS_X509_FMT_DER);
				if (ret < 0)
					continue;

				break;
			default:
				break;
			}
		}
	}

	/* Make sure last bag is freed */
	if (bag)
		gnutls_pkcs12_bag_deinit(bag);

	/* Free in case of error */
	if (ret < 0 && ret != GNUTLS_E_REQUESTED_DATA_NOT_AVAILABLE) {
		if (*x5)
			gnutls_x509_crt_deinit(*x5);
		if (*pkey)
			gnutls_x509_privkey_deinit(*pkey);
		if (friendly_name && *friendly_name)
			ufwissl_free(*friendly_name);
	}

	if (ret == GNUTLS_E_REQUESTED_DATA_NOT_AVAILABLE)
		ret = 0;
	return ret;
}

ufwissl_ssl_client_cert *ufwissl_ssl_clicert_read(const char *filename)
{
	int ret;
	gnutls_datum data;
	gnutls_pkcs12 p12;
	ufwissl_ssl_client_cert *cc;
	char *friendly_name = NULL;
	gnutls_x509_crt cert = NULL;
	gnutls_x509_privkey pkey = NULL;

	if (read_to_datum(filename, &data))
		return NULL;

	if (gnutls_pkcs12_init(&p12) != 0) {
		return NULL;
	}

	ret = gnutls_pkcs12_import(p12, &data, GNUTLS_X509_FMT_DER, 0);
	ufwissl_free(data.data);
	if (ret < 0) {
		gnutls_pkcs12_deinit(p12);
		return NULL;
	}

	if (gnutls_pkcs12_verify_mac(p12, "") == 0) {
		if (pkcs12_parse(p12, &pkey, &cert, &friendly_name, "") !=
		    0) {
			gnutls_pkcs12_deinit(p12);
			return NULL;
		}

		cc = ufwissl_calloc(sizeof *cc);
		cc->pkey = pkey;
		cc->decrypted = 1;
		cc->friendly_name = friendly_name;
		populate_cert(&cc->cert, cert);
		gnutls_pkcs12_deinit(p12);
		cc->p12 = NULL;
		return cc;
	} else {
		/* TODO: calling pkcs12_parse() here to find the friendly_name
		 * seems to break horribly.  */
		cc = ufwissl_calloc(sizeof *cc);
		cc->p12 = p12;
		return cc;
	}
}

int ufwissl_ssl_clicert_encrypted(const ufwissl_ssl_client_cert * cc)
{
	return !cc->decrypted;
}

int ufwissl_ssl_clicert_decrypt(ufwissl_ssl_client_cert * cc,
			      const char *password)
{
	int ret;
	gnutls_x509_crt cert = NULL;
	gnutls_x509_privkey pkey = NULL;

	if (gnutls_pkcs12_verify_mac(cc->p12, password) != 0) {
		return -1;
	}

	ret = pkcs12_parse(cc->p12, &pkey, &cert, NULL, password);
	if (ret < 0)
		return ret;

	gnutls_pkcs12_deinit(cc->p12);
	populate_cert(&cc->cert, cert);
	cc->pkey = pkey;
	cc->decrypted = 1;
	cc->p12 = NULL;
	return 0;
}

const ufwissl_ssl_certificate *ufwissl_ssl_clicert_owner(const
						     ufwissl_ssl_client_cert
						     * cc)
{
	return &cc->cert;
}

const char *ufwissl_ssl_clicert_name(const ufwissl_ssl_client_cert * ccert)
{
	return ccert->friendly_name;
}

ufwissl_ssl_certificate *ufwissl_ssl_cert_read(const char *filename)
{
	int ret;
	gnutls_datum data;
	gnutls_x509_crt x5;

	if (read_to_datum(filename, &data))
		return NULL;

	if (gnutls_x509_crt_init(&x5) != 0)
		return NULL;

	ret = gnutls_x509_crt_import(x5, &data, GNUTLS_X509_FMT_PEM);
	ufwissl_free(data.data);
	if (ret < 0) {
		gnutls_x509_crt_deinit(x5);
		return NULL;
	}

	return
	    populate_cert(ufwissl_calloc
			  (sizeof(struct ufwissl_ssl_certificate_s)), x5);
}

int ufwissl_ssl_cert_write(const ufwissl_ssl_certificate * cert,
			 const char *filename)
{
	unsigned char buffer[10 * 1024];
	size_t len = sizeof buffer;

	FILE *fp = fopen(filename, "w");

	if (fp == NULL)
		return -1;

	if (gnutls_x509_crt_export
	    (cert->subject, GNUTLS_X509_FMT_PEM, buffer, &len) < 0) {
		fclose(fp);
		return -1;
	}

	if (fwrite(buffer, len, 1, fp) != 1) {
		fclose(fp);
		return -1;
	}

	if (fclose(fp) != 0)
		return -1;

	return 0;
}

void ufwissl_ssl_cert_free(ufwissl_ssl_certificate * cert)
{
	gnutls_x509_crt_deinit(cert->subject);
	if (cert->identity)
		ufwissl_free(cert->identity);
	if (cert->issuer)
		ufwissl_ssl_cert_free(cert->issuer);
	ufwissl_free(cert);
}

int ufwissl_ssl_cert_cmp(const ufwissl_ssl_certificate * c1,
		       const ufwissl_ssl_certificate * c2)
{
	char digest1[UFWISSL_SSL_DIGESTLEN], digest2[UFWISSL_SSL_DIGESTLEN];

	if (ufwissl_ssl_cert_digest(c1, digest1)
	    || ufwissl_ssl_cert_digest(c2, digest2)) {
		return -1;
	}

	return strcmp(digest1, digest2);
}

ufwissl_ssl_client_cert *ufwissl_ssl_import_keypair(const char *cert_file,
						const char *key_file)
{
	ufwissl_ssl_client_cert *keypair = NULL;
	gnutls_datum cert_raw;
	gnutls_datum key_raw;

	keypair = ufwissl_calloc(sizeof(ufwissl_ssl_client_cert));
	if (keypair == NULL)
		return NULL;

	keypair->decrypted = 1;
	keypair->p12 = NULL;
	keypair->friendly_name = NULL;


	if (gnutls_x509_crt_init(&keypair->cert.subject) < 0)
		return NULL;
	if (read_to_datum(cert_file, &cert_raw) != UFWISSL_OK)
		return NULL;
	if (gnutls_x509_crt_import
	    (keypair->cert.subject, &cert_raw, GNUTLS_X509_FMT_PEM) < 0)
		return NULL;

	if (populate_cert(&keypair->cert, keypair->cert.subject) == NULL)
		return NULL;

	if (gnutls_x509_privkey_init(&keypair->pkey) < 0)
		return NULL;

	if (read_to_datum(key_file, &key_raw) != UFWISSL_OK)
		return NULL;
	if (gnutls_x509_privkey_import
	    (keypair->pkey, &key_raw, GNUTLS_X509_FMT_PEM) < 0)
		return NULL;

	return keypair;
}

/* The certificate import/export format is the base64 encoding of the
 * raw DER; PEM without the newlines and wrapping. */

ufwissl_ssl_certificate *ufwissl_ssl_cert_import(const char *data)
{
	int ret;
	size_t len;
	unsigned char *der;
	gnutls_datum buffer = { NULL, 0 };
	gnutls_x509_crt x5;

	if (gnutls_x509_crt_init(&x5) != 0)
		return NULL;

	/* decode the base64 to get the raw DER representation */
	len = ufwissl_unbase64(data, &der);
	if (len == 0)
		return NULL;

	buffer.data = der;
	buffer.size = len;

	ret = gnutls_x509_crt_import(x5, &buffer, GNUTLS_X509_FMT_DER);
	ufwissl_free(der);

	if (ret < 0) {
		gnutls_x509_crt_deinit(x5);
		return NULL;
	}

	return
	    populate_cert(ufwissl_calloc
			  (sizeof(struct ufwissl_ssl_certificate_s)), x5);
}

char *ufwissl_ssl_cert_export(const ufwissl_ssl_certificate * cert)
{
	unsigned char *der;
	size_t len = 0;
	char *ret;

	/* find the length of the DER encoding. */
	if (gnutls_x509_crt_export
	    (cert->subject, GNUTLS_X509_FMT_DER, NULL,
	     &len) != GNUTLS_E_SHORT_MEMORY_BUFFER) {
		return NULL;
	}

	der = ufwissl_malloc(len);
	if (gnutls_x509_crt_export
	    (cert->subject, GNUTLS_X509_FMT_DER, der, &len)) {
		ufwissl_free(der);
		return NULL;
	}

	ret = ufwissl_base64(der, len);
	ufwissl_free(der);
	return ret;
}

int ufwissl_ssl_cert_digest(const ufwissl_ssl_certificate * cert, char *digest)
{
	char sha1[20], *p;
	int j;
	size_t len = sizeof sha1;

	if (gnutls_x509_crt_get_fingerprint(cert->subject, GNUTLS_DIG_SHA,
					    sha1, &len) < 0)
		return -1;

	for (j = 0, p = digest; j < 20; j++) {
		*p++ = UFWISSL_HEX2ASC((sha1[j] >> 4) & 0x0f);
		*p++ = UFWISSL_HEX2ASC(sha1[j] & 0x0f);
		*p++ = ':';
	}

	*--p = '\0';
	return 0;
}

int ufwissl_get_peer_dn(ufwissl_session * sess, char *buf, size_t * buf_size)
{
	if (sess->peer_cert == NULL)
		return UFWISSL_ERROR;

	if (gnutls_x509_crt_get_dn
	    (sess->peer_cert->subj_dn.cert, buf, buf_size))
		return UFWISSL_ERROR;

	return UFWISSL_OK;
}

void *ufwissl_get_ctx(ufwissl_session * sess)
{
	if (!sess || !sess->ssl_context)
		return NULL;

	return NULL;
}

int ufwissl__ssl_init(void)
{
#ifdef UFWISSL_HAVE_TS_SSL
	gcry_control(GCRYCTL_SET_THREAD_CBS, &gcry_threads_pthread);
#endif
	return gnutls_global_init();
}

void ufwissl__ssl_exit(void)
{
	/* No way to unregister the thread callbacks.  Doomed. */
#if LIBGNUTLS_VERSION_MAJOR > 1 || LIBGNUTLS_VERSION_MINOR > 3 \
	|| (LIBGNUTLS_VERSION_MINOR == 3 && LIBGNUTLS_VERSION_PATCH >= 3)
	/* It's safe to call gnutls_global_deinit() here only with
	 * gnutls >= 1.3., since older versions don't refcount and
	 * doing so would prevent any other use of gnutls within
	 * the process. */
	gnutls_global_deinit();
#endif
}

int ufwissl_ssl_accept(ufwissl_ssl_socket * ssl, unsigned int timeout, char *errbuf, size_t errbufsz)
{
	gnutls_session session = *(gnutls_session*)ssl;
	int ret, continue_loop=1;
	int sock;
	int blocking_state;
	int was_writing=0;
	fd_set fd_r, fd_w;
	struct timeval tv;

	if (timeout == 0) {
		ret = gnutls_handshake(session);
		if (ret == 0)
			return 1; /* success */
		else
			return -1;
	}

	sock = (int) (long)gnutls_transport_get_ptr(session);
	blocking_state = fcntl(sock,F_GETFL);

	fcntl(sock,F_SETFL,(fcntl(sock,F_GETFL)|O_NONBLOCK));

	ret = -1;

	do {
		ret = gnutls_handshake(session);
		if (ret == 0) {
			/* handshake ok */
			ret = 1;
			continue_loop = 0;
			break;
		}
		if (gnutls_error_is_fatal(ret)) {
			snprintf(errbuf, errbufsz, "%s", gnutls_strerror(ret));
			ret = -1;
			continue_loop = 0;
			break;
		}
		switch (ret) {
			case GNUTLS_E_AGAIN:
			case GNUTLS_E_INTERRUPTED:
				was_writing = gnutls_record_get_direction(session);
				break;
			default:
				snprintf(errbuf, errbufsz, "%s", gnutls_strerror(ret));
				ret = -1;
				continue_loop = 0;
				break;
		}

		/* we need to wait before continuing the handshake */
		FD_ZERO(&fd_r);
		FD_ZERO(&fd_w);
		tv.tv_usec = 0;
		tv.tv_sec = timeout;
		if (was_writing) { FD_SET(sock,&fd_w); }
		else { FD_SET(sock,&fd_r); }

		ret = select(sock + 1, &fd_r, &fd_w, NULL, &tv);

		if ( ! (FD_ISSET(sock,&fd_r) || FD_ISSET(sock,&fd_w)) ) {
			/* timeout */
			continue_loop = 0;
			ret = 0;
			break;
		}
		ret = 1;
	} while (continue_loop);

	/* restore blocking state */
	fcntl(sock,F_SETFL,blocking_state);

	return ret;
}

#endif				/* HAVE_GNUTLS */
