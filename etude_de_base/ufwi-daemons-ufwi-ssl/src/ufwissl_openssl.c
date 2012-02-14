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
   neon SSL/TLS support using OpenSSL
   Copyright (C) 2007, Joe Orton <joe@manyfish.co.uk>
   Portions are:
   Copyright (C) 1999-2000 Tommi Komulainen <Tommi.Komulainen@iki.fi>

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

#ifdef HAVE_OPENSSL

#include "ufwissl_privssl.h"

#include <sys/types.h>

#ifdef HAVE_STRING_H
#include <string.h>
#endif

#include <stdio.h>

#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/pkcs12.h>
#include <openssl/x509v3.h>
#include <openssl/rand.h>

#ifdef UFWISSL_HAVE_TS_SSL
#include <stdlib.h>		/* for abort() */
#include <pthread.h>
#endif

#include <fcntl.h>

#include <ev.h>

#include "ufwissl_ssl.h"
#include "ufwissl_ssl_common.h"
#include "ufwissl_string.h"
#include "ufwissl_session.h"
#include "ufwissl_internal.h"

#include "ufwissl_private.h"
#include "ufwissl_privssl.h"
#include "ufwissl_utils.h"

/* OpenSSL 0.9.6 compatibility */
#if OPENSSL_VERSION_NUMBER < 0x0090700fL
#define PKCS12_unpack_authsafes M_PKCS12_unpack_authsafes
#define PKCS12_unpack_p7data M_PKCS12_unpack_p7data
/* cast away lack of const-ness */
#define OBJ_cmp(a,b) OBJ_cmp((ASN1_OBJECT *)(a), (ASN1_OBJECT *)(b))
#endif

/* Second argument for d2i_X509() changed type in 0.9.8. */
#if OPENSSL_VERSION_NUMBER < 0x0090800fL
typedef unsigned char ufwissl_d2i_uchar;
#else
typedef const unsigned char ufwissl_d2i_uchar;
#endif

/* Append an ASN.1 DirectoryString STR to buffer BUF as UTF-8.
 * Returns zero on success or non-zero on error. */
static int append_dirstring(ufwissl_buffer * buf, ASN1_STRING * str)
{
	unsigned char *tmp = (unsigned char *) "";	/* initialize to workaround 0.9.6 bug */
	int len;

	switch (str->type) {
	case V_ASN1_UTF8STRING:
	case V_ASN1_IA5STRING:	/* definitely ASCII */
	case V_ASN1_VISIBLESTRING:	/* probably ASCII */
	case V_ASN1_PRINTABLESTRING:	/* subset of ASCII */
		ufwissl_buffer_append(buf, (char *) str->data, str->length);
		break;
	case V_ASN1_UNIVERSALSTRING:
	case V_ASN1_T61STRING:	/* let OpenSSL convert it as ISO-8859-1 */
	case V_ASN1_BMPSTRING:
		len = ASN1_STRING_to_UTF8(&tmp, str);
		if (len > 0) {
			ufwissl_buffer_append(buf, (char *) tmp, len);
			OPENSSL_free(tmp);
			break;
		} else {
			ERR_clear_error();
			return -1;
		}
		break;
	default:
		UFWISSL_DEBUG(UFWISSL_DBG_SSL,
			    "Could not convert DirectoryString type %d\n",
			    str->type);
		return -1;
	}
	return 0;
}

/* Returns a malloc-allocate version of IA5 string AS.  Really only
 * here to prevent char * vs unsigned char * type mismatches without
 * losing all hope at type-safety. */
static char *dup_ia5string(const ASN1_IA5STRING * as)
{
	unsigned char *data = as->data;
	return ufwissl_strndup((char *) data, as->length);
}

char *ufwissl_ssl_readable_dname(const ufwissl_ssl_dname * name)
{
	int n, flag = 0;
	ufwissl_buffer *dump = ufwissl_buffer_create();
	const ASN1_OBJECT *const cname = OBJ_nid2obj(NID_commonName),
	    *const email = OBJ_nid2obj(NID_pkcs9_emailAddress);

	for (n = X509_NAME_entry_count(name->dn); n > 0; n--) {
		X509_NAME_ENTRY *ent =
		    X509_NAME_get_entry(name->dn, n - 1);

		/* Skip commonName or emailAddress except if there is no other
		 * attribute in dname. */
		if ((OBJ_cmp(ent->object, cname)
		     && OBJ_cmp(ent->object, email)) || (!flag
							 && n == 1)) {
			if (flag++)
				ufwissl_buffer_append(dump, ", ", 2);

			if (append_dirstring(dump, ent->value))
				ufwissl_buffer_czappend(dump, "???");
		}
	}

	return ufwissl_buffer_finish(dump);
}

int ufwissl_ssl_dname_cmp(const ufwissl_ssl_dname * dn1,
			const ufwissl_ssl_dname * dn2)
{
	return X509_NAME_cmp(dn1->dn, dn2->dn);
}

void ufwissl_ssl_clicert_free(ufwissl_ssl_client_cert * cc)
{
	if (cc->p12)
		PKCS12_free(cc->p12);
	if (cc->decrypted) {
		if (cc->cert.identity)
			ufwissl_free(cc->cert.identity);
		EVP_PKEY_free(cc->pkey);
		X509_free(cc->cert.subject);
	}
	if (cc->friendly_name)
		ufwissl_free(cc->friendly_name);
	ufwissl_free(cc);
}

/* Format an ASN1 time to a string. 'buf' must be at least of size
 * 'UFWISSL_SSL_VDATELEN'. */
static time_t asn1time_to_timet(const ASN1_TIME * atm)
{
	struct tm tm;
	int i = atm->length;

	if (i < 10)
		return (time_t) - 1;

	tm.tm_year = (atm->data[0] - '0') * 10 + (atm->data[1] - '0');

	/* Deal with Year 2000 */
	if (tm.tm_year < 70)
		tm.tm_year += 100;

	tm.tm_mon = (atm->data[2] - '0') * 10 + (atm->data[3] - '0') - 1;
	tm.tm_mday = (atm->data[4] - '0') * 10 + (atm->data[5] - '0');
	tm.tm_hour = (atm->data[6] - '0') * 10 + (atm->data[7] - '0');
	tm.tm_min = (atm->data[8] - '0') * 10 + (atm->data[9] - '0');
	tm.tm_sec = (atm->data[10] - '0') * 10 + (atm->data[11] - '0');

#ifdef HAVE_TIMEZONE
	/* ANSI C time handling is... interesting. */
	return mktime(&tm) - timezone;
#else
	return mktime(&tm);
#endif
}

void ufwissl_ssl_cert_validity_time(const ufwissl_ssl_certificate * cert,
				  time_t * from, time_t * until)
{
	if (from) {
		*from = asn1time_to_timet(X509_get_notBefore(cert->subject));
	}
	if (until) {
		*until = asn1time_to_timet(X509_get_notAfter(cert->subject));
	}
}

/* Return non-zero if hostname from certificate (cn) matches hostname
 * used for session (hostname).  Doesn't implement complete RFC 2818
 * logic; omits "f*.example.com" support for simplicity. */
static int match_hostname(char *cn, const char *hostname)
{
	const char *dot;

	dot = strchr(hostname, '.');
	if (dot == NULL) {
		char *pnt = strchr(cn, '.');
		/* hostname is not fully-qualified; unqualify the cn. */
		if (pnt != NULL) {
			*pnt = '\0';
		}
	} else if (strncmp(cn, "*.", 2) == 0) {
		hostname = dot + 1;
		cn += 2;
	}

	return !ufwissl_strcasecmp(cn, hostname);
}

/* Check certificate identity.  Returns zero if identity matches; 1 if
 * identity does not match, or <0 if the certificate had no identity.
 * If 'identity' is non-NULL, store the malloc-allocated identity in
 * *identity.  Logic specified by RFC 2818 and RFC 3280. */
/* static int check_identity(const ufwissl_uri *server, X509 *cert, char **identity) */
static int check_identity(const char *expected_hostname, X509 * cert, char **identity)
{
	STACK_OF(GENERAL_NAME) * names;
	int match = 0, found = 0;
	char *found_hostname = NULL;

/*     hostname = server ? server->host : ""; */

	names = X509_get_ext_d2i(cert, NID_subject_alt_name, NULL, NULL);
	/* if expected_hostname is NULL, do not check subjectAltName,
	 * we are only looking for the CN
	 */
	if (names && expected_hostname != NULL) {
		int n;

		/* subjectAltName contains a sequence of GeneralNames */
		for (n = 0; n < sk_GENERAL_NAME_num(names) && !match; n++) {
			GENERAL_NAME *nm = sk_GENERAL_NAME_value(names, n);

			/* handle dNSName and iPAddress name extensions only. */
			if (nm->type == GEN_DNS) {
				found_hostname = dup_ia5string(nm->d.ia5);
				match = match_hostname(found_hostname, expected_hostname);
				if (match) {
					found = 1;
					if (identity)
						*identity = ufwissl_strdup(found_hostname);
				}
			}
			else
			if (nm->type == GEN_IPADD) {
				/* compare IP address with server IP address. */
				ufwissl_inet_addr *ia;
				if (nm->d.ip->length == 4)
					ia = ufwissl_iaddr_make(ufwissl_iaddr_ipv4, nm->d.ip->data);
				else if (nm->d.ip->length == 16)
					ia = ufwissl_iaddr_make(ufwissl_iaddr_ipv6, nm->d.ip->data);
				else
					ia = NULL;
				/* ufwissl_iaddr_make returns NULL if address type is unsupported */
/*                 if (ia != NULL) { /\* address type was supported. *\/ */
/*                     char buf[128]; */

/*                     match = strcmp(hostname,  */
/*                                    ufwissl_iaddr_print(ia, buf, sizeof buf)) == 0; */
/*                     found = 1; */
/*                     ufwissl_iaddr_free(ia); */
/*                 } else { */
/*                     UFWISSL_DEBUG(UFWISSL_DBG_SSL, "iPAddress name with unsupported " */
/*                              "address type (length %d), skipped.\n", */
/*                              nm->d.ip->length); */
/*                 } */
			}
/*             else if (nm->type == GEN_URI) { */
/*                 char *name = dup_ia5string(nm->d.ia5); */
/*                 ufwissl_uri uri; */

/*                 if (ufwissl_uri_parse(name, &uri) == 0 && uri.host && uri.scheme) { */
/*                     ufwissl_uri tmp; */

/*                     if (identity && !found) *identity = ufwissl_strdup(name); */
/*                     found = 1; */

/*                     if (server) { */
/*                         /\* For comparison purposes, all that matters is */
/*                          * host, scheme and port; ignore the rest. *\/ */
/*                         memset(&tmp, 0, sizeof tmp); */
/*                         tmp.host = uri.host; */
/*                         tmp.scheme = uri.scheme; */
/*                         tmp.port = uri.port; */

/*                         match = ufwissl_uri_cmp(server, &tmp) == 0; */
/*                     } */
/*                 } */

/*                 ufwissl_uri_free(&uri); */
/*                 ufwissl_free(name); */
/*             } */
		}
	}

	/* free the whole stack. */
	if (names)
		sk_GENERAL_NAME_pop_free(names, GENERAL_NAME_free);

	/* Check against the commonName if no DNS alt. names were found,
	 * as per RFC3280. */
	if (!found) {
		X509_NAME *subj = X509_get_subject_name(cert);
		X509_NAME_ENTRY *entry;
		ufwissl_buffer *cname = ufwissl_buffer_ncreate(30);
		int idx = -1, lastidx;

		/* find the most specific commonName attribute. */
		do {
			lastidx = idx;
			idx = X509_NAME_get_index_by_NID(subj,
						       NID_commonName,
						       lastidx);
		} while (idx >= 0);

		/* check commonName attribute if present */
		if (lastidx >= 0) {
			/* extract the string from the entry */
			entry = X509_NAME_get_entry(subj, lastidx);
			if (append_dirstring(cname, X509_NAME_ENTRY_get_data(entry))) {
				ufwissl_buffer_destroy(cname);
				return -1;
			}

			found_hostname = ufwissl_strdup(cname->data);
			if (expected_hostname != NULL)
				match = match_hostname(found_hostname, expected_hostname);
		}
		ufwissl_buffer_destroy(cname);
	}

	if (found_hostname == NULL)
		return 1;

	/*UFWISSL_DEBUG(UFWISSL_DBG_SSL, "Identity match for '%s' (identity: %s): %s\n",
			expected_hostname, found_hostname,
			match ? "good" : "bad");*/
	if (identity != NULL)
		*identity = ufwissl_strdup(found_hostname);
	ufwissl_free(found_hostname);
	return match ? 0 : 1;
}

/* Populate an ufwissl_ssl_certificate structure from an X509 object. */
static ufwissl_ssl_certificate *populate_cert(ufwissl_ssl_certificate * cert,
					    X509 * x5)
{
	cert->subj_dn.dn = X509_get_subject_name(x5);
	cert->issuer_dn.dn = X509_get_issuer_name(x5);
	cert->issuer = NULL;
	cert->subject = x5;
	/* Retrieve the cert identity; pass a dummy hostname to match. */
	cert->identity = NULL;
	check_identity(NULL, x5, &cert->identity);
	return cert;
}

/* Return a linked list of certificate objects from an OpenSSL chain. */
static ufwissl_ssl_certificate *make_chain(STACK_OF(X509) * chain)
{
	int n, count = sk_X509_num(chain);
	ufwissl_ssl_certificate *top = NULL, *current = NULL;

	UFWISSL_DEBUG(UFWISSL_DBG_SSL, "Chain depth: %d\n", count);

	for (n = 0; n < count; n++) {
		ufwissl_ssl_certificate *cert = ufwissl_malloc(sizeof *cert);
		populate_cert(cert, X509_dup(sk_X509_value(chain, n)));
#if defined(UFWISSL_DEBUGGING) && !defined(_WIN32)
		if (ufwissl_debug_mask & UFWISSL_DBG_SSL) {
			fprintf(ufwissl_debug_stream, "Cert #%d:\n", n);
			X509_print_fp(ufwissl_debug_stream, cert->subject);
		}
#endif
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
static int check_certificate(ufwissl_session * sess, SSL * ssl,
			     ufwissl_ssl_certificate * chain)
{
	X509 *cert = chain->subject;
	ASN1_TIME *notBefore = X509_get_notBefore(cert);
	ASN1_TIME *notAfter = X509_get_notAfter(cert);
	int ret, failures = 0;
	long result;

	/* check expiry dates */
	if (X509_cmp_current_time(notBefore) >= 0)
		failures |= UFWISSL_SSL_NOTYETVALID;
	else if (X509_cmp_current_time(notAfter) <= 0)
		failures |= UFWISSL_SSL_EXPIRED;

	/* Check certificate was issued to this server; pass URI of
	 * server. */
	ret = check_identity(sess->server.hostname, cert, NULL);
	if (ret < 0) {
		ufwissl_set_error(sess,
				_("Server certificate was missing commonName "
				 "attribute in subject name"));
		return UFWISSL_ERROR;
	} else if (ret > 0) {
		if (sess->flags[UFWISSL_SESSFLAG_IGNORE_ID_MISMATCH] == 0)
			failures |= UFWISSL_SSL_IDMISMATCH;
	}

	/* get the result of the cert verification out of OpenSSL */
	result = SSL_get_verify_result(ssl);

	UFWISSL_DEBUG(UFWISSL_DBG_SSL, "Verify result: %ld = %s\n", result,
		    X509_verify_cert_error_string(result));

	switch (result) {
	case X509_V_ERR_UNABLE_TO_GET_ISSUER_CERT_LOCALLY:
	case X509_V_ERR_SELF_SIGNED_CERT_IN_CHAIN:
	case X509_V_ERR_DEPTH_ZERO_SELF_SIGNED_CERT:
		/* TODO: and probably more result codes here... */
		failures |= UFWISSL_SSL_UNTRUSTED;
		break;
		/* ignore these, since we've already noticed them: */
	case X509_V_ERR_CERT_NOT_YET_VALID:
	case X509_V_ERR_CERT_HAS_EXPIRED:
		/* cert was trusted: */
	case X509_V_OK:
		break;
	default:
		/* TODO: tricky to handle the 30-odd failure cases OpenSSL
		 * presents here (see x509_vfy.h), and present a useful API to
		 * the application so it in turn can then present a meaningful
		 * UI to the user.  The only thing to do really would be to
		 * pass back the error string, but that's not localisable.  So
		 * just fail the verification here - better safe than
		 * sorry. */
		ufwissl_set_error(sess,
				_("Certificate verification error: %s"),
				X509_verify_cert_error_string(result));
		return UFWISSL_ERROR;
	}

	if (failures == 0) {
		/* verified OK! */
		ret = UFWISSL_OK;
	} else {
		/* Set up the error string. */
		ufwissl__ssl_set_verify_err(sess, failures);
		ret = UFWISSL_ERROR;
		/* Allow manual override */
#if XXX
		if (sess->ssl_verify_fn &&
		    sess->ssl_verify_fn(sess->ssl_verify_ud, failures,
					chain) == 0)
			ret = UFWISSL_OK;
#endif
	}

	return ret;
}

/* Duplicate a client certificate, which must be in the decrypted state. */
static ufwissl_ssl_client_cert *dup_client_cert(const ufwissl_ssl_client_cert *
					      cc)
{
	ufwissl_ssl_client_cert *newcc = ufwissl_calloc(sizeof *newcc);

	newcc->decrypted = 1;
	newcc->pkey = cc->pkey;
	if (cc->friendly_name)
		newcc->friendly_name = ufwissl_strdup(cc->friendly_name);

	populate_cert(&newcc->cert, cc->cert.subject);

	cc->cert.subject->references++;
	cc->pkey->references++;
	return newcc;
}

#if 0
/* Callback invoked when the SSL server requests a client certificate.  */
static int provide_client_cert(SSL * ssl, X509 ** cert, EVP_PKEY ** pkey)
{
	ufwissl_session *const sess = SSL_get_app_data(ssl);

#if XXX
	if (!sess->my_cert && sess->ssl_provide_fn) {
		ufwissl_ssl_dname **dnames = NULL;
		int n, count = 0;
		STACK_OF(X509_NAME) * ca_list =
		    SSL_get_client_CA_list(ssl);

		count = ca_list ? sk_X509_NAME_num(ca_list) : 0;

		if (count > 0) {
			dnames =
			    ufwissl_malloc(count *
					 sizeof(ufwissl_ssl_dname *));

			for (n = 0; n < count; n++) {
				dnames[n] =
				    ufwissl_malloc(sizeof(ufwissl_ssl_dname));
				dnames[n]->dn =
				    sk_X509_NAME_value(ca_list, n);
			}
		}

		UFWISSL_DEBUG(UFWISSL_DBG_SSL,
			    "Calling client certificate provider...\n");
		sess->ssl_provide_fn(sess->ssl_provide_ud, sess,
				     (const ufwissl_ssl_dname *
				      const *) dnames, count);
		if (count) {
			for (n = 0; n < count; n++)
				ufwissl_free(dnames[n]);
			ufwissl_free(dnames);
		}
	}
#endif

	if (sess->my_cert) {
		ufwissl_ssl_client_cert *const cc = sess->my_cert;
		UFWISSL_DEBUG(UFWISSL_DBG_SSL,
			    "Supplying client certificate.\n");
		cc->pkey->references++;
		cc->cert.subject->references++;
		*cert = cc->cert.subject;
		*pkey = cc->pkey;
		return 1;
	} else {
		UFWISSL_DEBUG(UFWISSL_DBG_SSL,
			    "No client certificate supplied.\n");
		return 0;
	}
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

#ifdef BLAH
int ufwissl_ssl_set_clicert(ufwissl_session * sess,
			  const ufwissl_ssl_client_cert * cc)
{
	int ret;
	sess->my_cert = dup_client_cert(cc);

	if (sess->my_cert == NULL)
		return UFWISSL_ERROR;

	ret = SSL_CTX_use_PrivateKey(sess->ssl_context->ctx, cc->pkey);

	if (ret != 1)
		return UFWISSL_ERROR;

	ret =
	    SSL_CTX_use_certificate(sess->ssl_context->ctx->ctx,
				    cc->cert.subject);
	return (ret == 1) ? UFWISSL_OK : UFWISSL_ERROR;
}
#endif

int ufwissl__ssl_post_handshake(ufwissl_session * sess)
{
	ufwissl_ssl_context *ctx = sess->ssl_context;
	SSL *ssl;
	STACK_OF(X509) * chain;
	int freechain = 0;	/* non-zero if chain should be free'd. */

	UFWISSL_DEBUG(UFWISSL_DBG_SSL, "Doing SSL post-handshake checks. (check: %d)\n", sess->check_peer_cert);

	if (!sess->check_peer_cert)
		return UFWISSL_OK;

	/* Pass through the hostname if SNI is enabled. */
	ctx->hostname = sess->flags[UFWISSL_SESSFLAG_TLS_SNI] ?
		sess->server.hostname : NULL;

	ssl = ufwissl__sock_sslsock(sess->socket);

	chain = SSL_get_peer_cert_chain(ssl);
	/* For an SSLv2 connection, the cert chain will always be NULL. */
	/* The server-side must call SSL_get_peer_certificate
	 * (see SSL_get_peer_cert_chain(3)
	 */
	if (chain == NULL || sess->mode == UFWISSL_SSL_CTX_SERVER) {
		X509 *cert = SSL_get_peer_certificate(ssl);
		if (cert) {
			chain = sk_X509_new_null();
			sk_X509_push(chain, cert);
			freechain = 1;
		}
	}

	if (sess->check_peer_cert) {
		if (chain == NULL || sk_X509_num(chain) == 0) {
UFWISSL_DEBUG(UFWISSL_DBG_SSL, "SSL peer did not present certificate\n");
			ufwissl_set_error(sess, _("SSL peer did not present certificate"));
			if (sess->ssl_context->verify < 2) {
				/* certificates are not mandatory, so continue */
				return UFWISSL_OK;
			}
			return UFWISSL_ERROR;
		}

		if (sess->peer_cert) {
			int diff = X509_cmp(sk_X509_value(chain, 0),
				     sess->peer_cert->subject);
			if (freechain)
				sk_X509_free(chain);	/* no longer need the chain */
			if (diff) {
				/* This could be a MITM attack: fail the request. */
				ufwissl_set_error(sess,
						_("Server certificate changed: "
						 "connection intercepted?"));
				return UFWISSL_ERROR;
			}
			/* certificate has already passed verification: no need to
			 * verify it again. */
		} else {
			/* new connection: create the chain. */
			ufwissl_ssl_certificate *cert = make_chain(chain);

			if (freechain)
				sk_X509_free(chain);	/* no longer need the chain */

			if (check_certificate(sess, ssl, cert)) {
				UFWISSL_DEBUG(UFWISSL_DBG_SSL,
					    "SSL certificate checks failed: %s\n",
					    sess->error);
				ufwissl_ssl_cert_free(cert);
				return UFWISSL_ERROR;
			}
			/* remember the chain. */
			sess->peer_cert = cert;
		}
	}

	if (ctx->sess) {
		SSL_SESSION *newsess = SSL_get0_session(ssl);
		/* Replace the session if it has changed. */
		if (newsess != ctx->sess
		    || SSL_SESSION_cmp(ctx->sess, newsess)) {
			SSL_SESSION_free(ctx->sess);
			ctx->sess = SSL_get1_session(ssl);	/* bumping the refcount */
		}
	} else {
		/* Store the session. */
		ctx->sess = SSL_get1_session(ssl);
	}

	return UFWISSL_OK;
}

/* For internal use only. */
int ufwissl__negotiate_ssl(ufwissl_session * sess)
{
	ufwissl_ssl_context *ctx = sess->ssl_context;
	SSL *ssl;
	STACK_OF(X509) * chain;
	int freechain = 0;	/* non-zero if chain should be free'd. */

	UFWISSL_DEBUG(UFWISSL_DBG_SSL, "Doing SSL negotiation.\n");

	/* Pass through the hostname if SNI is enabled. */
	ctx->hostname =
	    sess->flags[UFWISSL_SESSFLAG_TLS_SNI] ? sess->server.
	    hostname : NULL;

	if (ufwissl_sock_connect_ssl(sess->socket, ctx, sess)) {
		if (ctx->sess) {
			/* remove cached session. */
			SSL_SESSION_free(ctx->sess);
			ctx->sess = NULL;
		}
		ufwissl_set_error(sess, _("SSL negotiation failed: %s"),
				ufwissl_sock_error(sess->socket));
		return UFWISSL_ERROR;
	}

	ssl = ufwissl__sock_sslsock(sess->socket);

	chain = SSL_get_peer_cert_chain(ssl);
	/* For an SSLv2 connection, the cert chain will always be NULL. */
	if (chain == NULL) {
		X509 *cert = SSL_get_peer_certificate(ssl);
		if (cert) {
			chain = sk_X509_new_null();
			sk_X509_push(chain, cert);
			freechain = 1;
		}
	}

	if (sess->check_peer_cert) {
		if (chain == NULL || sk_X509_num(chain) == 0) {
			ufwissl_set_error(sess,
					_
					("SSL server did not present certificate"));
			return UFWISSL_ERROR;
		}

		if (sess->peer_cert) {
			int diff =
			    X509_cmp(sk_X509_value(chain, 0),
				     sess->peer_cert->subject);
			if (freechain)
				sk_X509_free(chain);	/* no longer need the chain */
			if (diff) {
				/* This could be a MITM attack: fail the request. */
				ufwissl_set_error(sess,
						_
						("Server certificate changed: "
						 "connection intercepted?"));
				return UFWISSL_ERROR;
			}
			/* certificate has already passed verification: no need to
			 * verify it again. */
		} else {
			/* new connection: create the chain. */
			ufwissl_ssl_certificate *cert = make_chain(chain);

			if (freechain)
				sk_X509_free(chain);	/* no longer need the chain */

			if (check_certificate(sess, ssl, cert)) {
				UFWISSL_DEBUG(UFWISSL_DBG_SSL,
					    "SSL certificate checks failed: %s\n",
					    sess->error);
				ufwissl_ssl_cert_free(cert);
				return UFWISSL_ERROR;
			}
			/* remember the chain. */
			sess->peer_cert = cert;
		}
	}

	if (ctx->sess) {
		SSL_SESSION *newsess = SSL_get0_session(ssl);
		/* Replace the session if it has changed. */
		if (newsess != ctx->sess
		    || SSL_SESSION_cmp(ctx->sess, newsess)) {
			SSL_SESSION_free(ctx->sess);
			ctx->sess = SSL_get1_session(ssl);	/* bumping the refcount */
		}
	} else {
		/* Store the session. */
		ctx->sess = SSL_get1_session(ssl);
	}

	return UFWISSL_OK;
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

void ufwissl_ssl_trust_default_ca(ufwissl_session * sess)
{
	X509_STORE *store = SSL_CTX_get_cert_store(sess->ssl_context->ctx);

#ifdef UFWISSL_SSL_CA_BUNDLE
	X509_STORE_load_locations(store, UFWISSL_SSL_CA_BUNDLE, NULL);
#else
	X509_STORE_set_default_paths(store);
#endif
}

/* Find a friendly name in a PKCS12 structure the hard way, without
 * decrypting the parts which are encrypted.. */
static char *find_friendly_name(PKCS12 * p12)
{
	STACK_OF(PKCS7) * safes = PKCS12_unpack_authsafes(p12);
	int n, m;
	char *name = NULL;

	if (safes == NULL)
		return NULL;

	/* Iterate over the unpacked authsafes: */
	for (n = 0; n < sk_PKCS7_num(safes) && !name; n++) {
		PKCS7 *safe = sk_PKCS7_value(safes, n);
		STACK_OF(PKCS12_SAFEBAG) * bags;

		/* Only looking for unencrypted authsafes. */
		if (OBJ_obj2nid(safe->type) != NID_pkcs7_data)
			continue;

		bags = PKCS12_unpack_p7data(safe);
		if (!bags)
			continue;

		/* Iterate through the bags, picking out a friendly name */
		for (m = 0; m < sk_PKCS12_SAFEBAG_num(bags) && !name; m++) {
			PKCS12_SAFEBAG *bag =
			    sk_PKCS12_SAFEBAG_value(bags, m);
			name = PKCS12_get_friendlyname(bag);
		}

		sk_PKCS12_SAFEBAG_pop_free(bags, PKCS12_SAFEBAG_free);
	}

	sk_PKCS7_pop_free(safes, PKCS7_free);
	return name;
}

ufwissl_ssl_client_cert *ufwissl_ssl_clicert_read(const char *filename)
{
	PKCS12 *p12;
	FILE *fp;
	X509 *cert;
	EVP_PKEY *pkey;
	ufwissl_ssl_client_cert *cc;

	fp = fopen(filename, "rb");
	if (fp == NULL)
		return NULL;

	p12 = d2i_PKCS12_fp(fp, NULL);

	fclose(fp);

	if (p12 == NULL) {
		ERR_clear_error();
		return NULL;
	}

	/* Try parsing with no password. */
	if (PKCS12_parse(p12, NULL, &pkey, &cert, NULL) == 1) {
		/* Success - no password needed for decryption. */
		int len = 0;
		unsigned char *name = X509_alias_get0(cert, &len);

		cc = ufwissl_calloc(sizeof *cc);
		cc->pkey = pkey;
		cc->decrypted = 1;
		if (name && len > 0)
			cc->friendly_name =
			    ufwissl_strndup((char *) name, len);
		populate_cert(&cc->cert, cert);
		PKCS12_free(p12);
		return cc;
	} else {
		/* Failed to parse the file */
		int err = ERR_get_error();
		ERR_clear_error();
		if (ERR_GET_LIB(err) == ERR_LIB_PKCS12 &&
		    ERR_GET_REASON(err) == PKCS12_R_MAC_VERIFY_FAILURE) {
			/* Decryption error due to bad password. */
			cc = ufwissl_calloc(sizeof *cc);
			cc->friendly_name = find_friendly_name(p12);
			cc->p12 = p12;
			return cc;
		} else {
			/* Some parse error, give up. */
			PKCS12_free(p12);
			return NULL;
		}
	}
}

int ufwissl_ssl_clicert_encrypted(const ufwissl_ssl_client_cert * cc)
{
	return !cc->decrypted;
}

int ufwissl_ssl_clicert_decrypt(ufwissl_ssl_client_cert * cc,
			      const char *password)
{
	X509 *cert;
	EVP_PKEY *pkey;

	if (PKCS12_parse(cc->p12, password, &pkey, &cert, NULL) != 1) {
		ERR_clear_error();
		return -1;
	}

	if (X509_check_private_key(cert, pkey) != 1) {
		ERR_clear_error();
		X509_free(cert);
		EVP_PKEY_free(pkey);
		UFWISSL_DEBUG(UFWISSL_DBG_SSL,
			    "Decrypted private key/cert are not matched.");
		return -1;
	}

	PKCS12_free(cc->p12);
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

ufwissl_ssl_certificate *ufwissl_ssl_cert_mem_read_x509(void *cert_x509)
{
	X509 *cert = (X509 *) cert_x509;

	if (cert == NULL) {
		UFWISSL_DEBUG(UFWISSL_DBG_SSL, "d2i_X509_fp failed: %s\n",
			    ERR_reason_error_string(ERR_get_error()));
		ERR_clear_error();
		return NULL;
	}

	return populate_cert(ufwissl_calloc(sizeof(struct ufwissl_ssl_certificate_s)), cert);
}

ufwissl_ssl_certificate *ufwissl_ssl_cert_file_read(const char *filename)
{
	FILE *fp = fopen(filename, "r");
	X509 *cert;

	if (fp == NULL)
		return NULL;

	cert = PEM_read_X509(fp, NULL, NULL, NULL);
	fclose(fp);

	if (cert == NULL) {
		UFWISSL_DEBUG(UFWISSL_DBG_SSL, "d2i_X509_fp failed: %s\n",
			    ERR_reason_error_string(ERR_get_error()));
		ERR_clear_error();
		return NULL;
	}

	return populate_cert(ufwissl_calloc(sizeof(struct ufwissl_ssl_certificate_s)), cert);
}

int ufwissl_ssl_cert_write(const ufwissl_ssl_certificate * cert,
			 const char *filename)
{
	FILE *fp = fopen(filename, "w");

	if (fp == NULL)
		return -1;

	if (PEM_write_X509(fp, cert->subject) != 1) {
		ERR_clear_error();
		fclose(fp);
		return -1;
	}

	if (fclose(fp) != 0)
		return -1;

	return 0;
}

void ufwissl_ssl_cert_free(ufwissl_ssl_certificate * cert)
{
	X509_free(cert->subject);
	if (cert->issuer)
		ufwissl_ssl_cert_free(cert->issuer);
	if (cert->identity)
		ufwissl_free(cert->identity);
	ufwissl_free(cert);
}

int ufwissl_ssl_cert_cmp(const ufwissl_ssl_certificate * c1,
		       const ufwissl_ssl_certificate * c2)
{
	return X509_cmp(c1->subject, c2->subject);
}

static int check_crl_validity(ufwissl_session * sess, const char *crl_file, const char *ca_file)
{
	BIO* crl_bio;
	BIO* ca_bio;
	X509_CRL* crl;
	X509 *ca=NULL;
	EVP_PKEY *pkey;
	int ret;

	UFWISSL_DEBUG(UFWISSL_DBG_SOCKET, "Loading CRL: %s\n", crl_file);

	crl_bio = BIO_new(BIO_s_file());
	BIO_read_filename(crl_bio, crl_file);

	if (crl_bio == NULL)
		return UFWISSL_FAILED;

	crl = PEM_read_bio_X509_CRL(crl_bio, NULL, NULL, NULL);
	BIO_free(crl_bio);
	if (crl == NULL)
		return UFWISSL_FAILED;

	ca_bio = BIO_new_file(ca_file, "rb");
	if (ca_bio == NULL) {
		X509_CRL_free(crl);
		return UFWISSL_FAILED;
	}

	ca = PEM_read_bio_X509(ca_bio, NULL, NULL, NULL);
	if (ca == NULL) {
		X509_CRL_free(crl);
		BIO_free(ca_bio);
		return UFWISSL_FAILED;
	}

	pkey = X509_get_pubkey(ca);

	BIO_free(ca_bio);

	if (pkey == NULL)
	{
		EVP_PKEY_free(pkey);
		X509_CRL_free(crl);
		X509_free(ca);
		ufwissl_set_error(sess, _("CRL check failed: could not extract certificate authority public key from %s: %s\n"),ca_file,ERR_error_string(ERR_get_error(), NULL));
		return UFWISSL_FAILED;
	}

	// Check the validity of the CRL against the CA
	ret = X509_CRL_verify(crl, pkey);
	EVP_PKEY_free(pkey);
	if (ret <= 0)
	{
		/* Note that we cannot use ERR_error_string(ERR_get_error(), NULL)
		 * here, it returns something completely useless like:
		 * Error: 67567722 : error:0407006A:rsa routines:RSA_padding_check_PKCS1_type_1:block type is not 01
		 * In human-readable form, this means the CRL is not signed by the CA ...
		 */
		const char * errmsg = ERR_error_string(ERR_get_error(), NULL);
		/* TODO find a way to warn user without exiting */
		ufwissl_set_error(sess, "CRL check failed. Is CRL issued by the same Certificate Authority ? (%s)\n", errmsg);
		UFWISSL_DEBUG(UFWISSL_DBG_SSL, "CRL check failed. Is CRL issued by the same Certificate Authority ? (%s)\n", errmsg);
	}
	if (X509_cmp_current_time(X509_CRL_get_nextUpdate(crl)) < 0
			|| X509_cmp_current_time(X509_CRL_get_lastUpdate(crl)) > 0)
	{
		/* TODO find a way to warn user without exiting */
		ufwissl_set_error(sess, "CRL check failed: CRL has expired\n");
		UFWISSL_DEBUG(UFWISSL_DBG_SSL, "CRL check failed. CRL has expired\n");
	}

	X509_free(ca);
	X509_CRL_free(crl);

	return UFWISSL_OK;
}

/*
 * If the same CRL was updated (re-issued), we
 * don't know if this is properly reloaded, so patch openssl
 * See http://www.open.com.au/pipermail/radiator/2009-November/015911.html
 * http://rt.openssl.org/Ticket/Display.html?id=1893
 */
static int X509_STORE_add_or_replace_crl(X509_STORE *ctx, X509_CRL *x)
{
	X509_OBJECT *obj;
	int idx;

	if (x == NULL) return 0;
	obj = (X509_OBJECT *)OPENSSL_malloc(sizeof(X509_OBJECT));
	if (obj == NULL) {
		X509err(X509_F_X509_STORE_ADD_CRL,ERR_R_MALLOC_FAILURE);
		return 0;
	}
	obj->type = X509_LU_CRL;
	obj->data.crl = x;

	CRYPTO_w_lock(CRYPTO_LOCK_X509_STORE);

	X509_OBJECT_up_ref_count(obj);

	idx = sk_X509_OBJECT_find(ctx->objs, obj);
	if (idx >= 0) {
		X509_OBJECT *obj_old;
		obj_old = sk_X509_OBJECT_delete(ctx->objs, idx);
		X509_OBJECT_free_contents(obj_old);
		OPENSSL_free(obj_old);
	}
	sk_X509_OBJECT_push(ctx->objs, obj);

	CRYPTO_w_unlock(CRYPTO_LOCK_X509_STORE);

	return 1;
}

int ufwissl_ssl_set_crl_file(ufwissl_session * sess, const char *crl_file, const char *ca_file)
{
	X509_STORE *store = SSL_CTX_get_cert_store(sess->ssl_context->ctx);
	STACK_OF(X509_INFO) *sk;
	X509_INFO *itmp;
	BIO *in;
	int i;
	int count = 0;
	int ret;
	unsigned long err;

	if (store == NULL)
		return UFWISSL_ERROR;

	if (check_crl_validity(sess, crl_file, ca_file) != 0) {
		return UFWISSL_FAILED;
	}

	in = BIO_new(BIO_s_file());
	if (in == NULL) {
		return UFWISSL_FAILED;
	}

	if (BIO_read_filename(in, crl_file) <= 0) {
		BIO_free(in);
		return UFWISSL_FAILED;
	}

	sk = PEM_X509_INFO_read_bio(in, NULL, NULL, NULL);
	BIO_free(in);

	if (sk == NULL) {
		ufwissl_set_error(sess, "CRL load failed: unable to get x509 info\n");
		return UFWISSL_FAILED;
	}

	for(i = 0; i < sk_X509_INFO_num(sk); i++) {
		itmp = sk_X509_INFO_value(sk, i);
		if(itmp->crl) {
			ERR_clear_error();
			ret = X509_STORE_add_or_replace_crl(store, itmp->crl);
			if (ret != 1) {
				/* specifically ignore the error if we are trying to load
				 * a CRL which was already loaded before
				 */
				err = ERR_get_error();
				if ((err & 0xff) == X509_R_CERT_ALREADY_IN_HASH_TABLE) {
					UFWISSL_DEBUG(UFWISSL_DBG_SSL, "Load CRL ignored (file %s index %d)\n",
							crl_file, i);
					count++;
					continue;
				}
				UFWISSL_DEBUG(UFWISSL_DBG_SSL, "Load CRL failed (file %s index %d): %d\n",
						crl_file, i, ret);
				UFWISSL_DEBUG(UFWISSL_DBG_SOCKET,
						"ssl: error in X509_STORE_add_crl %lx: %s\n",
						err, ERR_error_string(err,NULL));
			}
			count++;
		}
	}
	sk_X509_INFO_pop_free(sk, X509_INFO_free);

	if (count > 0) {
		X509_STORE_set_flags(store, X509_V_FLAG_CRL_CHECK | X509_V_FLAG_CRL_CHECK_ALL);
		return UFWISSL_OK;
	}

	return UFWISSL_ERROR;
}

int ufwissl_ssl_set_ca_file(ufwissl_session *sess, const char *cafile)
{
	STACK_OF(X509_INFO) *sk = NULL;
	STACK_OF(X509) *stack = NULL;
	ufwissl_ssl_certificate *ca;
	BIO *in = NULL;
	X509_INFO *xi;
	int num_certs, num_checked = 0;
	int i, ret = UFWISSL_ERROR;

	if (sess == NULL || sess->ssl_context == NULL)
		return UFWISSL_ERROR;

	stack = sk_X509_new_null();
	if ( !stack ) {
		ufwissl_set_error(sess, _("trust cert : memory allocation failure"));
		goto end;
	}

	in = BIO_new_file(cafile, "r");
	if ( !in ) {
		ufwissl_set_error(sess, _("trust cert : error opening the file"));
		goto end;
	}

	sk = PEM_X509_INFO_read_bio(in, NULL, NULL, NULL);
	if ( !sk ) {
		ufwissl_set_error(sess, _("trust cert : error reading the file"));
		goto end;
	}

	while ( sk_X509_INFO_num(sk) ) 	{
		xi = sk_X509_INFO_shift(sk);

		if ( xi->x509 != NULL ) {
			sk_X509_push(stack, xi->x509);
			xi->x509 = NULL;
		}

		X509_INFO_free(xi);
	}

	num_certs = sk_X509_num(stack);
	for ( i=0; i < num_certs; i++ ) {
		X509 *ucert = NULL;
		int res;

		ucert = sk_X509_value(stack, i);

		ca = ufwissl_ssl_cert_mem_read_x509(ucert);
		if ( ca ) {
			res = ufwissl_ssl_context_trustcert(sess->ssl_context, ca);

			if ( res == UFWISSL_OK )
				num_checked++;
		}
	}

	if ( num_checked ) {
		if ( num_checked == num_certs ) {
			ret = UFWISSL_OK;
		}
	}

end:
	if (in)
		BIO_free(in);

	if (sk)
		sk_X509_INFO_free(sk);

	if ( stack )
		sk_X509_free(stack);

	return ret;
}

ufwissl_ssl_client_cert *ufwissl_ssl_import_keypair(const char *cert_file,
						const char *key_file)
{
	FILE *fp;
	ufwissl_ssl_client_cert *keypair = NULL;

	keypair = ufwissl_calloc(sizeof(ufwissl_ssl_client_cert));
	if (keypair == NULL)
		return NULL;

	keypair->decrypted = 1;
	keypair->p12 = NULL;
	keypair->friendly_name = NULL;

	// Load the certificate
	fp = fopen(cert_file, "r");
	if (fp == NULL) {
		ufwissl_free(keypair);
		return NULL;
	}

	keypair->cert.subject = PEM_read_X509(fp, NULL, NULL, NULL);
	fclose(fp);
	if (keypair->cert.subject == NULL)
		return NULL;

	if (populate_cert(&keypair->cert, keypair->cert.subject) == NULL)
		return NULL;

	// Load the private key
	fp = fopen(key_file, "r");
	if (fp == NULL) {
		ufwissl_free(keypair);
		return NULL;
	}

	keypair->pkey = PEM_read_PrivateKey(fp, NULL, NULL, NULL);
	fclose(fp);
	if (keypair->pkey == NULL)
		return NULL;
	return keypair;
}

/* The certificate import/export format is the base64 encoding of the
 * raw DER; PEM without the newlines and wrapping. */

ufwissl_ssl_certificate *ufwissl_ssl_cert_import(const char *data)
{
	unsigned char *der;
	ufwissl_d2i_uchar *p;
	size_t len;
	X509 *x5;

	/* decode the base64 to get the raw DER representation */
	len = ufwissl_unbase64(data, &der);
	if (len == 0)
		return NULL;

	p = der;
	x5 = d2i_X509(NULL, &p, len);	/* p is incremented */
	ufwissl_free(der);
	if (x5 == NULL) {
		ERR_clear_error();
		return NULL;
	}

	return populate_cert(ufwissl_calloc
			  (sizeof(struct ufwissl_ssl_certificate_s)), x5);
}

char *ufwissl_ssl_cert_export(const ufwissl_ssl_certificate * cert)
{
	int len;
	unsigned char *der, *p;
	char *ret;

	/* find the length of the DER encoding. */
	len = i2d_X509(cert->subject, NULL);

	p = der = ufwissl_malloc(len);
	i2d_X509(cert->subject, &p);	/* p is incremented */

	ret = ufwissl_base64(der, len);
	ufwissl_free(der);
	return ret;
}

#if SHA_DIGEST_LENGTH != 20
# error SHA digest length is not 20 bytes
#endif

int ufwissl_ssl_cert_digest(const ufwissl_ssl_certificate * cert, char *digest)
{
	unsigned char sha1[EVP_MAX_MD_SIZE];
	unsigned int len, j;
	char *p;

	if (!X509_digest(cert->subject, EVP_sha1(), sha1, &len)
	    || len != 20) {
		ERR_clear_error();
		return -1;
	}

	for (j = 0, p = digest; j < 20; j++) {
		*p++ = UFWISSL_HEX2ASC((sha1[j] >> 4) & 0x0f);
		*p++ = UFWISSL_HEX2ASC(sha1[j] & 0x0f);
		*p++ = ':';
	}

	p[-1] = '\0';
	return 0;
}

int ufwissl_get_peer_dn(ufwissl_session * sess, char *buf, size_t * buf_size)
{
	BIO *mem;
	char *data = NULL;
	size_t datalen;
	int flags = XN_FLAG_SEP_COMMA_PLUS | XN_FLAG_DN_REV;

	if (!sess || !sess->peer_cert || !sess->peer_cert->subj_dn.dn)
		return UFWISSL_ERROR;

	mem = BIO_new(BIO_s_mem());

	if (X509_NAME_print_ex(mem, sess->peer_cert->subj_dn.dn, 0, flags)) {
		datalen = BIO_get_mem_data(mem, &data);
		if (datalen > *buf_size)
			datalen = *buf_size;
		memcpy(buf, data, datalen);
		buf[datalen] = '\0';
		*buf_size = datalen;
		BIO_free(mem);

		return UFWISSL_OK;
	}

	BIO_free(mem);

	return UFWISSL_ERROR;
}

void *ufwissl_get_ctx(ufwissl_session * sess)
{
	if (!sess || !sess->ssl_context)
		return NULL;

	return sess->ssl_context->ctx;
}

#ifdef UFWISSL_HAVE_TS_SSL
/* Implementation of locking callbacks to make OpenSSL thread-safe.
 * If the OpenSSL API was better designed, this wouldn't be necessary.
 * In OpenSSL releases without CRYPTO_set_idptr_callback, it's not
 * possible to implement the locking in a POSIX-compliant way, since
 * it's necessary to cast from a pthread_t to an unsigned long at some
 * point.  */

static pthread_mutex_t *locks;
static size_t num_locks;

#ifndef HAVE_CRYPTO_SET_IDPTR_CALLBACK
/* Named to be obvious when it shows up in a backtrace. */
static unsigned long thread_id_neon(void)
{
	/* This will break if pthread_t is a structure; upgrading OpenSSL
	 * >= 0.9.9 (which does not require this callback) is the only
	 * solution.  */
	return (unsigned long) pthread_self();
}
#endif

/* Another great API design win for OpenSSL: no return value!  So if
 * the lock/unlock fails, all that can be done is to abort. */
static void thread_lock_neon(int mode, int n, const char *file, int line)
{
	if (mode & CRYPTO_LOCK) {
		if (pthread_mutex_lock(&locks[n])) {
			abort();
		}
	} else {
		if (pthread_mutex_unlock(&locks[n])) {
			abort();
		}
	}
}

#endif

/* ID_CALLBACK_IS_{NEON,OTHER} evaluate as true if the currently
 * registered OpenSSL ID callback is the neon function (_NEON), or has
 * been overwritten by some other app (_OTHER). */
#ifdef HAVE_CRYPTO_SET_IDPTR_CALLBACK
#define ID_CALLBACK_IS_OTHER (0)
#define ID_CALLBACK_IS_NEON (1)
#else
#define ID_CALLBACK_IS_OTHER (CRYPTO_get_id_callback() != NULL)
#define ID_CALLBACK_IS_NEON (CRYPTO_get_id_callback() == thread_id_neon)
#endif

int ufwissl__ssl_init(void)
{
	CRYPTO_malloc_init();
	SSL_load_error_strings();
	SSL_library_init();
	OpenSSL_add_all_algorithms();

#ifdef UFWISSL_HAVE_TS_SSL
	/* If some other library has already come along and set up the
	 * thread-safety callbacks, then it must be presumed that the
	 * other library will have a longer lifetime in the process than
	 * neon.  If the library which has installed the callbacks is
	 * unloaded, then all bets are off. */
	if (ID_CALLBACK_IS_OTHER || CRYPTO_get_locking_callback() != NULL) {
		UFWISSL_DEBUG(UFWISSL_DBG_SOCKET,
			    "ssl: OpenSSL thread-safety callbacks already installed.\n");
		UFWISSL_DEBUG(UFWISSL_DBG_SOCKET,
			    "ssl: neon will not replace existing callbacks.\n");
	} else {
		size_t n;

		num_locks = CRYPTO_num_locks();

		/* For releases where CRYPTO_set_idptr_callback is present,
		 * the default ID callback should be sufficient. */
#ifndef HAVE_CRYPTO_SET_IDPTR_CALLBACK
		CRYPTO_set_id_callback(thread_id_neon);
#endif
		CRYPTO_set_locking_callback(thread_lock_neon);

		locks = malloc(num_locks * sizeof *locks);
		for (n = 0; n < num_locks; n++) {
			if (pthread_mutex_init(&locks[n], NULL)) {
				UFWISSL_DEBUG(UFWISSL_DBG_SOCKET,
					    "ssl: Failed to initialize pthread mutex.\n");
				return -1;
			}
		}

		UFWISSL_DEBUG(UFWISSL_DBG_SOCKET,
			    "ssl: Initialized OpenSSL thread-safety callbacks "
			    "for %" UFWISSL_FMT_SIZE_T " locks.\n",
			    num_locks);
	}
#endif

	return 0;
}

void ufwissl__ssl_exit(void)
{
	/* Cannot call ERR_free_strings() etc here in case any other code
	 * in the process using OpenSSL. */

#ifdef UFWISSL_HAVE_TS_SSL
	/* Only unregister the callbacks if some *other* library has not
	 * come along in the mean-time and trampled over the callbacks
	 * installed by neon. */
	if (CRYPTO_get_locking_callback() == thread_lock_neon
	    && ID_CALLBACK_IS_NEON) {
		size_t n;

#ifndef HAVE_CRYPTO_SET_IDPTR_CALLBACK
		CRYPTO_set_id_callback(NULL);
#endif
		CRYPTO_set_locking_callback(NULL);

		for (n = 0; n < num_locks; n++) {
			pthread_mutex_destroy(&locks[n]);
		}

		free(locks);
	}
#endif
}

static void ssl_activity_cb(struct ev_loop *loop, ev_io *w, int revents)
{
	int sslerr, status;
	SSL *ssl= (SSL *)w->data;

	status = SSL_accept(ssl);
	sslerr = SSL_get_error(ssl,status);
	if (status == 1) {
		ev_io_stop(loop, w);
		ev_unloop(loop, EVUNLOOP_ONE);
		return;
	} else {
		switch (sslerr) {
			case SSL_ERROR_WANT_READ:
			case SSL_ERROR_WANT_WRITE:
				break;
			default:
				ev_io_stop(loop, w);
				ev_unloop(loop, EVUNLOOP_ONE);
				/* FIXME */
				//snprintf(errbuf, errbufsz, "%s", ERR_error_string(ERR_get_error(),NULL));
				UFWISSL_DEBUG(UFWISSL_DBG_SOCKET,
						"ssl: error in handshake %s\n",
						ERR_error_string(ERR_get_error(),NULL));
				w->data = NULL;
		}
		return;
	}
}


static void ssl_timeout_cb(struct ev_loop *loop, ev_timer *w, int revents)
{

	UFWISSL_DEBUG(UFWISSL_DBG_SOCKET,
			"ssl: timeout in ssl handshake\n");
	ev_io_stop(loop, w->data);
	ev_unloop(loop, EVUNLOOP_ONE);
	w->data = NULL;
}

int ufwissl_ssl_accept(ufwissl_ssl_socket * ssl_sock, unsigned int timeout, char *errbuf, size_t errbufsz)
{
	int ret;
	int sock;
	int blocking_state;
	SSL *ssl = *ssl_sock;
	struct ev_loop *loop;
	ev_io ssl_watcher;
	ev_timer timer;

	if (timeout == 0) {
		return SSL_accept(ssl);
	}

	sock = SSL_get_fd(ssl);
	blocking_state = fcntl(sock,F_GETFL);

	fcntl(sock,F_SETFL,(fcntl(sock,F_GETFL)|O_NONBLOCK));

	ret = -1;

	loop = ev_loop_new(0);
	ev_io_init(&ssl_watcher, ssl_activity_cb, sock , EV_READ|EV_WRITE);
	ssl_watcher.data = ssl;
	ev_io_start(loop, &ssl_watcher);
	ev_timer_init (&timer, ssl_timeout_cb, 1.0 * timeout, 0);
	timer.data = &ssl_watcher;
	ev_timer_start (loop, &timer);

	ev_loop(loop, 0);

	ev_loop_destroy(loop);

	if ((timer.data == NULL) || (ssl_watcher.data == NULL)) {
		ret = -1;
	} else {
		ret = 1;
	}

	fcntl(sock,F_SETFL,blocking_state);

	return ret;
}

#endif				/* HAVE_OPENSSL */
