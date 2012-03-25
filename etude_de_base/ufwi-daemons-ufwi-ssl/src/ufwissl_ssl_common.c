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

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "ufwissl_ssl_common.h"
#include "ufwissl_private.h"
#include "ufwissl_privssl.h"
#include "ufwissl_ssl.h"
#include "ufwissl_internal.h"
#include "ufwissl_alloc.h"

char *ufwissl_get_cert_info(ufwissl_session * sess)
{
	char valid_from[UFWISSL_SSL_VDATELEN];
	char valid_until[UFWISSL_SSL_VDATELEN];
	char *ret, *dn, *issuer_dn, *dn_str, *issuer_str, *from_str,
	    *until_str;

	if (!sess->my_cert)
		return NULL;

	dn = ufwissl_ssl_readable_dname(&sess->my_cert->cert.subj_dn);
	issuer_dn =
	    ufwissl_ssl_readable_dname(&sess->my_cert->cert.issuer_dn);
	ufwissl_ssl_cert_validity(&sess->my_cert->cert, valid_from,
				valid_until);

	dn_str = _("DN: ");
	issuer_str = _("Issuer DN: ");
	from_str = _("Valid from: ");
	until_str = _("Valid until: ");

	ret = (char *) malloc(strlen(dn) + strlen(issuer_dn) + strlen(valid_from) + strlen(valid_until) + strlen(dn_str) + strlen(issuer_str) + strlen(from_str) + strlen(until_str) + 5);	/* 5 = 4 '\n' and 1 '\0' */

	if (!ret) {
		ufwissl_free(dn);
		ufwissl_free(issuer_dn);
		return NULL;
	}

	strcpy(ret, dn_str);
	strcat(ret, dn);
	strcat(ret, "\n");
	strcat(ret, issuer_str);
	strcat(ret, issuer_dn);
	strcat(ret, "\n");
	strcat(ret, from_str);
	strcat(ret, valid_from);
	strcat(ret, "\n");
	strcat(ret, until_str);
	strcat(ret, valid_until);
	strcat(ret, "\n");

	ufwissl_free(dn);
	ufwissl_free(issuer_dn);

	return ret;
}

char *ufwissl_get_server_cert_info(ufwissl_session * sess)
{
	char valid_from[UFWISSL_SSL_VDATELEN];
	char valid_until[UFWISSL_SSL_VDATELEN];
	char *ret, *dn, *issuer_dn, *dn_str, *issuer_str, *from_str,
	    *until_str;

	if (!sess->peer_cert)
		return NULL;

	dn = ufwissl_ssl_readable_dname(&sess->peer_cert->subj_dn);
	issuer_dn = ufwissl_ssl_readable_dname(&sess->peer_cert->issuer_dn);
	ufwissl_ssl_cert_validity(sess->peer_cert, valid_from, valid_until);

	dn_str = _("DN: ");
	issuer_str = _("Issuer DN: ");
	from_str = _("Valid from: ");
	until_str = _("Valid until: ");

	ret = (char *) ufwissl_malloc(strlen(dn) + strlen(issuer_dn) + strlen(valid_from) + strlen(valid_until) + strlen(dn_str) + strlen(issuer_str) + strlen(from_str) + strlen(until_str) + 5);	/* 5 = 4 '\n' and 1 '\0' */

	if (!ret) {
		ufwissl_free(dn);
		ufwissl_free(issuer_dn);
		return NULL;
	}

	strcpy(ret, dn_str);
	strcat(ret, dn);
	strcat(ret, "\n");
	strcat(ret, issuer_str);
	strcat(ret, issuer_dn);
	strcat(ret, "\n");
	strcat(ret, from_str);
	strcat(ret, valid_from);
	strcat(ret, "\n");
	strcat(ret, until_str);
	strcat(ret, valid_until);
	strcat(ret, "\n");

	ufwissl_free(dn);
	ufwissl_free(issuer_dn);

	return ret;
}

char *ufwissl_get_server_cert_dn(ufwissl_session * sess)
{
	char *tmp, *dn;
	if (!sess->peer_cert) {
		ufwissl_set_error(sess,
				_("The peer didn't send a certificate."));
		return NULL;
	}

	tmp = ufwissl_ssl_readable_dname(&sess->peer_cert->subj_dn);
	dn = strdup(tmp);
	ufwissl_free(tmp);
	return dn;
}
