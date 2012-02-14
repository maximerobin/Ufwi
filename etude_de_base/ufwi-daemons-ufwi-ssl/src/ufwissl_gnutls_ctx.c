/*
 ** Copyright (C) 2007-2009 INL
 ** Written by S.Tricaud <stricaud@inl.fr>
 **            L.Defert <ldefert@inl.fr>
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

#include <dirent.h>

#include <gnutls/gnutls.h>
#include <gnutls/pkcs12.h>

#include <errno.h>
#include <pthread.h>
#include <gcrypt.h>

#ifdef HAVE_ICONV
#include <iconv.h>
#endif

#include "ufwissl_config.h"
#include "ufwissl_ssl_common.h"

#include "ufwissl_ssl.h"
#include "ufwissl_string.h"
#include "ufwissl_session.h"
#include "ufwissl_internal.h"

#include "ufwissl_private.h"
#include "ufwissl_privssl.h"
#include "ufwissl_utils.h"

int read_to_datum(const char *filename, gnutls_datum * datum);

ufwissl_ssl_context *ufwissl_ssl_context_create(int flags)
{
	ufwissl_ssl_context *ctx = ufwissl_calloc(sizeof *ctx);
	gnutls_certificate_allocate_credentials(&ctx->cred);
/*    if (flags == UFWISSL_SSL_CTX_CLIENT) {
        gnutls_certificate_client_set_retrieve_function(ctx->cred,
                                                        provide_client_cert);
    }*/
	return ctx;
}

#if 0
int ufwissl_ssl_context_keypair(ufwissl_ssl_context * ctx,
			      const char *cert, const char *key)
{
	return (gnutls_certificate_set_x509_key_file(ctx->cred, cert, key,
						     GNUTLS_X509_FMT_PEM)
		== 0) ? UFWISSL_OK : UFWISSL_ERROR;
}
#endif

int ufwissl_ssl_context_keypair_from_data(ufwissl_ssl_context * ctx,
					ufwissl_ssl_client_cert * cert)
{
	int ret;
	ret = gnutls_certificate_set_x509_key(ctx->cred, &cert->cert.subject,
					    1, cert->pkey);
	if (ret != 0)
		return UFWISSL_ERROR;
	gnutls_certificate_set_dh_params(ctx->cred, ctx->dh);

	return (ret == 0) ? UFWISSL_OK : UFWISSL_ERROR;
}

/* Server mode: Set DH parameters */
int ufwissl_ssl_context_set_dh_bits(ufwissl_ssl_context * ctx,
				  unsigned int dh_bits)
{
	ctx->dh_bits = dh_bits;

	if (gnutls_dh_params_init(&ctx->dh) < 0)
		return UFWISSL_ERROR;

	if (gnutls_dh_params_generate2(ctx->dh, ctx->dh_bits) < 0)
		return UFWISSL_ERROR;

	return UFWISSL_OK;
}

int ufwissl_ssl_context_set_dh_file(ufwissl_ssl_context * ctx,
				  const char *filename)
{
	gnutls_datum_t datum_dh;
	int ret;

	datum_dh.data = NULL;

	if (!filename)
		return UFWISSL_ERROR;

	/* read CRL and CA */
	ret = read_to_datum(filename, &datum_dh);
	if (ret != 0)
		return UFWISSL_ERROR;

	if (gnutls_dh_params_init(&ctx->dh) < 0) {
		free(datum_dh.data);
		return UFWISSL_ERROR;
	}

	if (gnutls_dh_params_import_pkcs3(ctx->dh, &datum_dh, GNUTLS_X509_FMT_PEM) < 0) {
		free(datum_dh.data);
		return UFWISSL_ERROR;
	}

	free(datum_dh.data);
	return UFWISSL_OK;
}

#if 0
int ufwissl_ssl_context_set_verify(ufwissl_ssl_context * ctx, int required,
				 const char *ca_names,
				 const char *verify_cas)
{
	ctx->verify = required;
	if (verify_cas) {
		gnutls_certificate_set_x509_trust_file(ctx->cred,
						       verify_cas,
						       GNUTLS_X509_FMT_PEM);
	}
	/* gnutls_certificate_send_x509_rdn_sequence in gnutls >= 1.2 can
	 * be used to *suppress* sending the CA names, but not control it,
	 * it seems. */
	return 0;
}
#endif

void ufwissl_ssl_context_set_flag(ufwissl_ssl_context * ctx, int flag,
				int value)
{
	/* SSLv2 not supported. */
}

void ufwissl_ssl_context_destroy(ufwissl_ssl_context * ctx)
{
	gnutls_certificate_free_credentials(ctx->cred);
	gnutls_dh_params_deinit(ctx->dh);
	if (ctx->cache.client.data) {
		ufwissl_free(ctx->cache.client.data);
	} else if (ctx->cache.server.key.data) {
		gnutls_free(ctx->cache.server.key.data);
		gnutls_free(ctx->cache.server.data.data);
	}
	if (ctx->ciphers)
		ufwissl_free(ctx->ciphers);
	ufwissl_free(ctx);
}

int ufwissl_ssl_context_trustcert(ufwissl_ssl_context * ctx,
				const ufwissl_ssl_certificate * cert)
{
	gnutls_x509_crt certs = cert->subject;
	return (gnutls_certificate_set_x509_trust(ctx->cred, &certs, 1) ==
		0) ? UFWISSL_OK : UFWISSL_ERROR;
}

/* Note: adding all CA here will cause the server to send the
 * complete list to the client when requesting cert, unless
 * gnutls_certificate_send_x509_rdn_sequence() is used.
 */

int ufwissl_ssl_context_trustdir(ufwissl_ssl_context * ctx,
				const char *capath)
{
	DIR *dirca = NULL;
	struct dirent *file;
	char path_fd[PATH_MAX];

	dirca = opendir(capath);
	if (dirca == NULL)
		return UFWISSL_ERROR;

	while ((file = readdir(dirca)) != NULL) {
#ifdef HAVE_STRUCT_DIRENT_D_TYPE
		if (!(file->d_type == DT_REG ||
		      file->d_type == DT_LNK))
			continue;
#endif

		if (!ufwissl_snprintf(path_fd, sizeof(path_fd), "%s/%s",
					capath, file->d_name))
			continue;

		if (gnutls_certificate_set_x509_trust_file(ctx->cred, path_fd, GNUTLS_X509_FMT_PEM) < 0) {
			UFWISSL_DEBUG(UFWISSL_DBG_SSL,
					"Ignoring CA file %s\n",
					path_fd);
			continue;
		}
	}

	closedir(dirca);

 return UFWISSL_OK;
}

#endif				/* HAVE_GNUTLS */
