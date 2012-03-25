/*
 ** Copyright (C) 2007-2009 INL
 ** Written by Pierre Chifflier <chifflier@inl.fr>
 ** INL http://www.inl.fr/
 **
 ** NuSSL: OpenSSL / GnuTLS layer based on libneon
 */

/*
   HTTP request/response handling
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

/* This is the HTTP client request/response implementation.
 * The goal of this code is to be modular and simple.
 */

#include <config.h>
#include "ufwissl_config.h"

#include <sys/types.h>

#include <errno.h>
#include <fcntl.h>
#ifdef HAVE_STRING_H
#include <string.h>
#endif
#ifdef HAVE_STRINGS_H
#include <strings.h>
#endif
#ifdef HAVE_STDLIB_H
#include <stdlib.h>
#endif
#ifdef HAVE_UNISTD_H
#include <unistd.h>
#endif

#include "ufwissl_privssl.h"
#include "ufwissl_internal.h"

#include "ufwissl_alloc.h"
#include "ufwissl_request.h"
#include "ufwissl_string.h"	/* for ufwissl_buffer */
#include "ufwissl_utils.h"
#include "ufwissl_socket.h"
#include "ufwissl_session.h"

#include "ufwissl_private.h"

#define SOCK_ERR(req, op, msg) do { ssize_t sret = (op); \
if (sret < 0) return aborted(req, msg, sret); } while (0)

#define EOL "\r\n"


struct field {
	char *name, *value;
	size_t vlen;
	struct field *next;
};

/* Maximum number of header fields per response: */
#define MAX_HEADER_FIELDS (100)
/* Size of hash table; 43 is the smallest prime for which the common
 * header names hash uniquely using the *33 hash function. */
#define HH_HASHSIZE (43)
/* Hash iteration step: *33 known to be a good hash for ASCII, see RSE. */
#define HH_ITERATE(hash, ch) (((hash)*33 + (unsigned char)(ch)) % HH_HASHSIZE)

/* pre-calculated hash values for given header names: */
#define HH_HV_CONNECTION        (0x14)
#define HH_HV_CONTENT_LENGTH    (0x13)
#define HH_HV_TRANSFER_ENCODING (0x07)

/* Return the first resolved address for the given host. */
static const ufwissl_inet_addr *resolve_first(ufwissl_session * sess,
					    struct host_info *host)
{
	if (sess->addrlist) {
		sess->curaddr = 0;
		return sess->addrlist[0];
	} else {
		return ufwissl_addr_first(host->address);
	}
}

/* Return the next resolved address for the given host or NULL if
 * there are no more addresses. */
static const ufwissl_inet_addr *resolve_next(ufwissl_session * sess,
					   struct host_info *host)
{
	if (sess->addrlist) {
		if (sess->curaddr++ < sess->numaddrs)
			return sess->addrlist[sess->curaddr];
		else
			return NULL;
	} else {
		return ufwissl_addr_next(host->address);
	}
}

/* Make new TCP connection to server at 'host' of type 'name'.  Note
 * that once a connection to a particular network address has
 * succeeded, that address will be used first for the next attempt to
 * connect. */
static int do_connect(ufwissl_session * sess, struct host_info *host,
		      const char *err)
{
	int ret;

	if ((sess->socket = ufwissl_sock_create()) == NULL) {
		ufwissl_set_error(sess, _("Could not create socket"));
		return UFWISSL_ERROR;
	}

	if (sess->cotimeout)
		ufwissl_sock_connect_timeout(sess->socket, sess->cotimeout);

	if (host->current == NULL)
		host->current = resolve_first(sess, host);

	sess->status.ci.hostname = host->hostname;

	do {
		sess->status.ci.address = host->current;
		/* notify_status(sess, ufwissl_status_connecting); */
#if defined(UFWISSL_DEBUGGING) && !defined(_WIN32)
		if (ufwissl_debug_mask & UFWISSL_DBG_HTTP) {
			char buf[150];
			UFWISSL_DEBUG(UFWISSL_DBG_HTTP, "Connecting to %s\n",
				    ufwissl_iaddr_print(host->current, buf,
						      sizeof buf));
		}
#endif
		ret = ufwissl_sock_connect(sess->socket, host->current,
				       host->port);
	} while (ret &&		/* try the next address... */
		 (host->current = resolve_next(sess, host)) != NULL);

	if (ret) {
		ufwissl_set_error(sess, "%s: %s", err,
				ufwissl_sock_error(sess->socket));
		return UFWISSL_CONNECT;
	}

	/* notify_status(sess, ufwissl_status_connected); */
	ufwissl_sock_read_timeout(sess->socket, sess->rdtimeout);

	/* clear persistent connection flag. */
	sess->persisted = 0;
	return UFWISSL_OK;
}

/* Perform any necessary DNS lookup for the host given by *info;
 * return UFWISSL_ code. */
static int lookup_host(ufwissl_session * sess, struct host_info *info)
{
	if (sess->addrlist)
		return UFWISSL_OK;

	UFWISSL_DEBUG(UFWISSL_DBG_HTTP, "Doing DNS lookup on %s...\n",
		    info->hostname);
	sess->status.lu.hostname = info->hostname;
	/*notify_status(sess, ufwissl_status_lookup); */
	info->address = ufwissl_addr_resolve(info->hostname, 0);
	if (ufwissl_addr_result(info->address)) {
		char buf[256];
		ufwissl_set_error(sess,
				_("Could not resolve hostname `%s': %s"),
				info->hostname,
				ufwissl_addr_error(info->address, buf,
						 sizeof buf));
		ufwissl_addr_destroy(info->address);
		info->address = NULL;
		return UFWISSL_LOOKUP;
	} else {
		return UFWISSL_OK;
	}
}

int ufwissl_open_connection(ufwissl_session * sess)
{
	int ret;
	struct host_info *host;

	if (sess->socket)
		return UFWISSL_OK;

	/* Resolve hostname if necessary. */
	host = &sess->server;
	if (host->address == NULL) {
		ret = lookup_host(sess, host);
		if (ret)
			return ret;
	}

	ret = do_connect(sess, host, _("Could not connect to server"));
	if (ret != UFWISSL_OK)
		return ret;

	/* Negotiate SSL layer. */
#ifdef XXX
	if ( /*sess->use_ssl && */ !sess->in_connect) {
		/* CONNECT tunnel */
		/*    if (sess->use_proxy)
		   ret = proxy_tunnel(sess); */
#endif
		if (ret == UFWISSL_OK) {
			ret = ufwissl__negotiate_ssl(sess);
		}
#ifdef XXX
	}
#endif

	return ret;
}
