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


#include "ufwissl_ssl.h"
#include "ufwissl_ssl_common.h"
#include "ufwissl_string.h"
#include "ufwissl_session.h"
#include "ufwissl_internal.h"

#include "ufwissl_private.h"
#include "ufwissl_privssl.h"
#include "ufwissl_utils.h"

ufwissl_ssl_context *ufwissl_ssl_context_create(int mode)
{
	ufwissl_ssl_context *ctx = ufwissl_calloc(sizeof *ctx);

	if (mode == UFWISSL_SSL_CTX_CLIENT) {
		ctx->ctx = SSL_CTX_new(SSLv23_client_method());
		ctx->sess = NULL;
		/* set client cert callback. */
		//SSL_CTX_set_client_cert_cb(ctx->ctx, provide_client_cert);
		/* enable workarounds for buggy SSL server implementations */
		SSL_CTX_set_options(ctx->ctx, SSL_OP_ALL);
	} else if (mode == UFWISSL_SSL_CTX_SERVER) {
		ctx->ctx = SSL_CTX_new(SSLv23_server_method());
		SSL_CTX_set_session_cache_mode(ctx->ctx,
					       SSL_SESS_CACHE_CLIENT);
	} else {
		ctx->ctx = SSL_CTX_new(SSLv2_server_method());
		SSL_CTX_set_session_cache_mode(ctx->ctx,
					       SSL_SESS_CACHE_CLIENT);
	}

	return ctx;
}

void ufwissl_ssl_context_set_flag(ufwissl_ssl_context * ctx, int flag,
				int value)
{
	long opts = SSL_CTX_get_options(ctx->ctx);

	switch (flag) {
	case UFWISSL_SSL_CTX_SSLv2:
		if (value) {
			/* Enable SSLv2 support; clear the "no SSLv2" flag. */
			opts &= ~SSL_OP_NO_SSLv2;
		} else {
			/* Disable it: set the flag. */
			opts |= SSL_OP_NO_SSLv2;
		}
		break;
	}

	SSL_CTX_set_options(ctx->ctx, opts);
}

int ufwissl_ssl_context_keypair(ufwissl_ssl_context * ctx, const char *cert,
			      const char *key)
{
	int ret;

	ret = SSL_CTX_use_PrivateKey_file(ctx->ctx, key, SSL_FILETYPE_PEM);
	if (ret == 1) {
		ret =
		    SSL_CTX_use_certificate_file(ctx->ctx, cert,
						 SSL_FILETYPE_PEM);
	}

	return ret == 1 ? 0 : -1;
}

int ufwissl_ssl_context_keypair_from_data(ufwissl_ssl_context * ctx,
					ufwissl_ssl_client_cert * cert)
{
	int ret;
	ret = SSL_CTX_use_PrivateKey(ctx->ctx, cert->pkey);

	if (ret != 1)
		return UFWISSL_ERROR;

	ret = SSL_CTX_use_certificate(ctx->ctx, cert->cert.subject);
	return (ret == 1) ? UFWISSL_OK : UFWISSL_ERROR;
}

int ufwissl_ssl_context_set_verify(ufwissl_ssl_context * ctx,
				 int required,
				 const char *ca_names,
				 const char *verify_cas)
{
	if (required) {
		int verify_mode = SSL_VERIFY_PEER;

		if (required == UFWISSL_CERT_REQUIRE)
			verify_mode |= SSL_VERIFY_FAIL_IF_NO_PEER_CERT;
		SSL_CTX_set_verify(ctx->ctx, verify_mode, NULL);
	}
	if (ca_names) {
		SSL_CTX_set_client_CA_list(ctx->ctx,
					   SSL_load_client_CA_file
					   (ca_names));
	}
	if (verify_cas) {
		SSL_CTX_load_verify_locations(ctx->ctx, verify_cas, NULL);
	}
	return 0;
}

void ufwissl_ssl_context_destroy(ufwissl_ssl_context * ctx)
{
	SSL_CTX_free(ctx->ctx);
	if (ctx->sess)
		SSL_SESSION_free(ctx->sess);
	if (ctx->ciphers)
		ufwissl_free(ctx->ciphers);
	ufwissl_free(ctx);
}

int ufwissl_ssl_context_trustcert(ufwissl_ssl_context * ctx,
				const ufwissl_ssl_certificate * cert)
{
	X509_STORE *store = SSL_CTX_get_cert_store(ctx->ctx);

	if (store == NULL)
		return UFWISSL_ERROR;

	return (X509_STORE_add_cert(store, cert->subject) ==
		1) ? UFWISSL_OK : UFWISSL_ERROR;
}

int ufwissl_ssl_context_trustdir(ufwissl_ssl_context * ctx,
				const char *capath)
{
	X509_STORE *store = SSL_CTX_get_cert_store(ctx->ctx);
	X509_LOOKUP *lookup;
	int ret;

	if (store == NULL)
		return UFWISSL_ERROR;

	lookup = X509_STORE_add_lookup(store, X509_LOOKUP_hash_dir());
	ret = X509_LOOKUP_add_dir(lookup, capath, X509_FILETYPE_PEM);
	return (ret > 0) ? UFWISSL_OK : UFWISSL_ERROR;
}

/* Server mode: Set DH parameters */
int ufwissl_ssl_context_set_dh_bits(ufwissl_ssl_context * ctx,
				  unsigned int dh_bits)
{
	DH *dh;

	ERR_clear_error();
	dh = DH_new();

	if (!DH_generate_parameters_ex(dh, dh_bits, 2, NULL)) {
		DH_free(dh);
		return UFWISSL_ERROR;
	}

	if (SSL_CTX_set_tmp_dh(ctx->ctx, dh) != 1) {
		DH_free(dh);
		return UFWISSL_ERROR;
	}

	ctx->dh = dh;

	return UFWISSL_OK;
}

int ufwissl_ssl_context_set_dh_file(ufwissl_ssl_context * ctx,
				  const char *filename)
{
	FILE *fp;
	DH *dh;

	fp = fopen(filename, "r+");
	if (fp == NULL)
		return UFWISSL_ERROR;

	dh = PEM_read_DHparams(fp, NULL, NULL, NULL);
	fclose(fp);

	if (dh == NULL)
		return UFWISSL_ERROR;

	if (SSL_CTX_set_tmp_dh(ctx->ctx, dh) != 1) {
		DH_free(dh);
		return UFWISSL_ERROR;
	}

	ctx->dh = dh;

	return UFWISSL_OK;
}


#endif				/* HAVE_OPENSSL */
