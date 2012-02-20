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

/** \defgroup NuSSL NuSSL Library
 * \brief This is a library used in NuFW to be independant from a specific TLS/SLL implementation.
 *
 * @{
 */

/**
 * \file ufwissl_session.c
 * \brief ufwissl session handling
 */

#include <config.h>


#include <string.h>
#include <stdlib.h>
#include <errno.h>
#include <sys/types.h>
#include <sys/stat.h>

#include <fcntl.h>

#include "ufwissl_privssl.h"
#include "ufwissl_session.h"
#include "ufwissl_alloc.h"
#include "ufwissl_utils.h"
#include "ufwissl_internal.h"
#include "ufwissl_string.h"
#include "ufwissl_dates.h"
#include "ufwissl_socket.h"

#include "ufwissl_private.h"

#ifdef UFWISSL_HAVE_TS_SSL
# include <pthread.h>
#endif

/* pre-declration list */
int ufwissl_session_get_fd(ufwissl_session * sess);

extern int ufwissl_ssl_set_ca_file(ufwissl_session *sess, const char *cafile);

#if 0
/* Destroy a a list of hooks. */
static void destroy_hooks(struct hook *hooks)
{
	struct hook *nexthk;

	while (hooks) {
		nexthk = hooks->next;
		ufwissl_free(hooks);
		hooks = nexthk;
	}
}
#endif

void ufwissl_session_destroy(ufwissl_session * sess)
{

	UFWISSL_DEBUG(UFWISSL_DBG_HTTP, "ufwissl_session_destroy called.\n");

	if (!sess)
		return;

	/* Close the connection; note that the notifier callback could
	 * still be invoked here. */
	ufwissl_close_connection(sess);

	ufwissl_free(sess->server.hostname);
	if (sess->server.address)
		ufwissl_addr_destroy(sess->server.address);

	if (sess->ssl_context)
		ufwissl_ssl_context_destroy(sess->ssl_context);

	if (sess->peer_cert)
		ufwissl_ssl_cert_free(sess->peer_cert);

	if (sess->my_cert)
		ufwissl_ssl_clicert_free(sess->my_cert);

	ufwissl_free(sess);

}

/* Stores the hostname/port in *sess, setting up the "hostport"
 * segment correctly. */
void ufwissl_set_hostinfo(ufwissl_session * sess, const char *hostname,
			unsigned int port)
{

	if (!sess)
		return;

	if (sess->server.hostname)
		ufwissl_free(sess->server.hostname);
	sess->server.hostname = ufwissl_strdup(hostname);
	sess->server.port = port;

}

/* Set list of allowed ciphers for TLS negotiation */
void ufwissl_session_set_ciphers(ufwissl_session * sess, const char *cipher_list)
{
	if (!sess)
		return;

	if (!sess->ssl_context)
		return;

	sess->ssl_context->ciphers = ufwissl_strdup(cipher_list);
}

ufwissl_session *ufwissl_session_create(int mode)
{

	ufwissl_session *sess = ufwissl_calloc(sizeof *sess);

/*    UFWISSL_DEBUG(UFWISSL_DBG_HTTP, "session to ://%s:%d begins.\n",
	     hostname, port); */

	if (!sess)
		return NULL;

	strcpy(sess->error, "Unknown error.");

	sess->ssl_context = ufwissl_ssl_context_create(mode);
	sess->flags[UFWISSL_SESSFLAG_SSLv2] = 1;
	sess->flags[UFWISSL_SESSFLAG_TLS_SNI] = 1;

	/* Set flags which default to on: */
	sess->flags[UFWISSL_SESSFLAG_PERSIST] = 1;

	/* Set default read timeout */
	sess->rdtimeout = SOCKET_READ_TIMEOUT;

	/* check certificates by default */
	sess->check_peer_cert = 1;

	sess->mode = mode;

	return sess;
}

/* Server function */
ufwissl_session *ufwissl_session_create_with_fd(int server_fd, int verify)
{
	ufwissl_session *srv_sess;
	srv_sess = ufwissl_session_create(UFWISSL_SSL_CTX_SERVER);
	if (!srv_sess) {
		return NULL;
	}

	srv_sess->socket = ufwissl_sock_create_with_fd(server_fd);
	/* verify: one of UFWISSL_CERT_IGNORE, UFWISSL_CERT_REQUEST or UFWISSL_CERT_REQUIRE */
	srv_sess->ssl_context->verify = verify;

	return srv_sess;
}

/* Server function */
ufwissl_session *ufwissl_session_accept(ufwissl_session * srv_sess)
{
	ufwissl_session *client_sess;

	if (!srv_sess)
		return NULL;

	client_sess = ufwissl_session_create(UFWISSL_SSL_CTX_SERVER);

	if (!client_sess) {
		ufwissl_set_error(srv_sess, _("Not enough memory"));
		return NULL;
	}

	if (srv_sess->ssl_context->verify)
		client_sess->check_peer_cert = 1;

	if (srv_sess->ssl_context->ciphers != NULL)
		ufwissl_session_set_ciphers(client_sess, srv_sess->ssl_context->ciphers);

	client_sess->socket = ufwissl_sock_create();

	/* TDOD: make ufwissl_sock_accept return a real error.. */
	if (ufwissl_sock_accept(client_sess->socket, ufwissl_sock_fd(srv_sess->socket)) != 0) {
		ufwissl_set_error(srv_sess,
				"Error during ufwissl_session_accept()\n");
		ufwissl_session_destroy(client_sess);
		return NULL;
	}

	return client_sess;
}

int ufwissl_session_handshake(ufwissl_session * client_sess, ufwissl_session * srv_sess)
{
	int fd;

	if (ufwissl_sock_accept_ssl(client_sess->socket, srv_sess->ssl_context)) {
		/* ufwissl_sock_accept_ssl already sets an error */
		ufwissl_set_error(srv_sess, "%s",
				ufwissl_sock_error(client_sess->socket));
		return -1;
	}
	// Post handshake needed to retrieve the peers certificate
	if (ufwissl__ssl_post_handshake(client_sess) != UFWISSL_OK) {
		/* ufwissl__ssl_post_handshake already sets an error */
		ufwissl_set_error(srv_sess, "%s",
				ufwissl_get_error(client_sess));
		return -1;
	}

	if (client_sess->rdtimeout > 0) {
		// Set non-blocking mode
		UFWISSL_DEBUG(UFWISSL_DBG_SSL, "Setting non-blocking mode\n");
		fd = ufwissl_session_get_fd(client_sess);
		fcntl(fd,F_SETFL,(fcntl(fd,F_GETFL)|O_NONBLOCK));
	}

	return 0;
}

int ufwissl_session_get_fd(ufwissl_session * sess)
{
	if (!sess)
		return -1;

	return ufwissl_sock_fd(sess->socket);
}

int ufwissl_session_get_cipher(ufwissl_session * sess, char *buf, size_t bufsz)
{
	char *cipher = NULL;

	if (!sess)
		return -1;

	cipher = ufwissl_sock_cipher(sess->socket);
	if (!cipher)
		return -1;

	strncpy(buf, cipher, bufsz);
	ufwissl_free(cipher);

	return 0;
}

int ufwissl_session_set_dh_bits(ufwissl_session * sess, unsigned int dh_bits)
{
	if (!sess)
		return UFWISSL_ERROR;

	return ufwissl_ssl_context_set_dh_bits(sess->ssl_context, dh_bits);
}

int ufwissl_session_set_dh_file(ufwissl_session * sess, const char *file)
{
	if (!sess)
		return UFWISSL_ERROR;

	return ufwissl_ssl_context_set_dh_file(sess->ssl_context, file);
}

void ufwissl_set_addrlist(ufwissl_session * sess,
			const ufwissl_inet_addr ** addrs, size_t n)
{
	if (!sess)
		return;

	sess->addrlist = addrs;
	sess->numaddrs = n;

}

void ufwissl_set_error(ufwissl_session * sess, const char *format, ...)
{
	va_list params;

	if (!sess)
		return;

	va_start(params, format);
	ufwissl_vsnprintf(sess->error, sizeof sess->error, format, params);
	va_end(params);
}

void ufwissl_set_session_flag(ufwissl_session * sess, ufwissl_session_flag flag,
			    int value)
{
	if (!sess)
		return;

	if (flag < UFWISSL_SESSFLAG_LAST) {
		sess->flags[flag] = value;
		if (flag == UFWISSL_SESSFLAG_SSLv2 && sess->ssl_context) {
			ufwissl_ssl_context_set_flag(sess->ssl_context,
						   UFWISSL_SSL_CTX_SSLv2,
						   value);
		}
	}
}

int ufwissl_get_session_flag(ufwissl_session * sess, ufwissl_session_flag flag)
{
	if (!sess)
		return -1;

	if (flag < UFWISSL_SESSFLAG_LAST) {
		int sess_flag = sess->flags[flag];

		return sess_flag;
	}
	return -1;
}

/* static void progress_notifier(void *userdata, ufwissl_session_status status, */
/*                               const ufwissl_session_status_info *info) */
/* { */
/*     ufwissl_session *sess = userdata; */

/*     if (status == ufwissl_status_sending || status == ufwissl_status_recving) { */
/*         sess->progress_cb(sess->progress_ud, info->sr.progress, info->sr.total);     */
/*     } */
/* } */

/* void ufwissl_set_progress(ufwissl_session *sess, ufwissl_progress progress, void *userdata) */
/* { */
/*     sess->progress_cb = progress; */
/*     sess->progress_ud = userdata; */
/*     ufwissl_set_notifier(sess, progress_notifier, sess); */
/* } */

/* void ufwissl_set_notifier(ufwissl_session *sess, */
/* 		     ufwissl_notify_status status, void *userdata) */
/* { */
/*     sess->notify_cb = status; */
/*     sess->notify_ud = userdata; */
/* } */

void ufwissl_set_read_timeout(ufwissl_session * sess, int timeout)
{
	if (!sess)
		return;

	sess->rdtimeout = timeout;

	if (sess->socket)
		ufwissl_sock_read_timeout(sess->socket, timeout);

}

void ufwissl_set_connect_timeout(ufwissl_session * sess, int timeout)
{
	if (!sess)
		return;

	sess->cotimeout = timeout;

	if (sess->socket)
		ufwissl_sock_connect_timeout(sess->socket, timeout);

}

const char *ufwissl_get_error(ufwissl_session * sess)
{
	char *ret;

	if (!sess)
		return NULL;

	ret = ufwissl_strclean(sess->error);

	return ret;
}

void ufwissl_close_connection(ufwissl_session * sess)
{
	if (!sess)
		return;

	if (sess->socket) {
		UFWISSL_DEBUG(UFWISSL_DBG_SOCKET, "Closing connection.\n");
		ufwissl_sock_close(sess->socket);
		sess->socket = NULL;
		UFWISSL_DEBUG(UFWISSL_DBG_SOCKET, "Connection closed.\n");
	} else {
		UFWISSL_DEBUG(UFWISSL_DBG_SOCKET,
			    "(Not closing closed connection!).\n");
	}
}

void ufwissl_ssl_disable_certificate_check(ufwissl_session * sess, int is_disabled)
{
	if (!sess)
		return;

	sess->check_peer_cert = !is_disabled;
}

#if 0
void ufwissl_ssl_set_verify(ufwissl_session * sess, ufwissl_ssl_verify_fn fn,
			  void *userdata)
{

	sess->ssl_verify_fn = fn;
	sess->ssl_verify_ud = userdata;

}

void ufwissl_ssl_provide_clicert(ufwissl_session * sess,
			       ufwissl_ssl_provide_fn fn, void *userdata)
{

	sess->ssl_provide_fn = fn;
	sess->ssl_provide_ud = userdata;

}
#endif

int ufwissl_ssl_trust_cert_file(ufwissl_session * sess, const char *cert_file)
{
	int ret;

	if (!sess)
		return UFWISSL_ERROR;

	ret = ufwissl_ssl_set_ca_file(sess, cert_file);

	if (ret == UFWISSL_OK)
		sess->check_peer_cert = 1;


	return ret;
}

int ufwissl_ssl_trust_dir(ufwissl_session * sess, const char *dir)
{
	int ret;

	if (!sess)
		return UFWISSL_ERROR;

	ret = ufwissl_ssl_context_trustdir(sess->ssl_context, dir);

	if (ret == UFWISSL_OK)
		sess->check_peer_cert = 1;


	return ret;
}

void ufwissl_ssl_cert_validity(const ufwissl_ssl_certificate * cert,
			     char *from, char *until)
{
	time_t tf, tu;
	char *date;

	if (!cert)
		return;

	ufwissl_ssl_cert_validity_time(cert, &tf, &tu);

	if (from) {
		if (tf != (time_t) - 1) {
			date = ufwissl_rfc1123_date(tf);
			ufwissl_strnzcpy(from, date, UFWISSL_SSL_VDATELEN);
			ufwissl_free(date);
		} else {
			ufwissl_strnzcpy(from, _("[invalid date]"),
				       UFWISSL_SSL_VDATELEN);
		}
	}

	if (until) {
		if (tu != (time_t) - 1) {
			date = ufwissl_rfc1123_date(tu);
			ufwissl_strnzcpy(until, date, UFWISSL_SSL_VDATELEN);
			ufwissl_free(date);
		} else {
			ufwissl_strnzcpy(until, _("[invalid date]"),
				       UFWISSL_SSL_VDATELEN);
		}
	}

}

void ufwissl__ssl_set_verify_err(ufwissl_session * sess, int failures)
{
	static const struct {
		int bit;
		const char *str;
	} reasons[] = {
		{
		UFWISSL_SSL_NOTYETVALID, N_("certificate is not yet valid")},
		{
		UFWISSL_SSL_EXPIRED, N_("certificate has expired")}, {
		UFWISSL_SSL_IDMISMATCH,
			    N_
			    ("certificate issued for a different hostname")},
		{
		UFWISSL_SSL_UNTRUSTED, N_("issuer is not trusted")}, {
		UFWISSL_SSL_INVALID,
			    N_("certificate is not a valid certificate")},
		{
		UFWISSL_SSL_REVOKED, N_("certificate is revoked")}, {
		UFWISSL_SSL_SIGNER_NOT_FOUND, N_("signer not found")}, {
		UFWISSL_SSL_SIGNER_NOT_CA, N_("signer not a CA")}, {
		0, NULL}
	};
	int n, flag = 0;

	strcpy(sess->error, _("Peer certificate verification failed: "));

	for (n = 0; reasons[n].bit; n++) {
		if (failures & reasons[n].bit) {
			if (flag)
				strncat(sess->error, ", ",
					sizeof sess->error);
			strncat(sess->error, _(reasons[n].str),
				sizeof sess->error);
			flag = 1;
		}
	}
}

#if 0
typedef void (*void_fn) (void);

#define ADD_HOOK(hooks, fn, ud) add_hook(&(hooks), NULL, (void_fn)(fn), (ud))

static void add_hook(struct hook **hooks, const char *id, void_fn fn,
		     void *ud)
{
	struct hook *hk = ufwissl_malloc(sizeof(struct hook)), *pos;

	if (*hooks != NULL) {
		for (pos = *hooks; pos->next != NULL; pos = pos->next)
			/* nullop */ ;
		pos->next = hk;
	} else {
		*hooks = hk;
	}

	hk->id = id;
	hk->fn = fn;
	hk->userdata = ud;
	hk->next = NULL;
}
#endif

/* void ufwissl_hook_create_request(ufwissl_session *sess,  */
/* 			    ufwissl_create_request_fn fn, void *userdata) */
/* { */
/*     ADD_HOOK(sess->create_req_hooks, fn, userdata); */
/* } */

/* void ufwissl_hook_pre_send(ufwissl_session *sess, ufwissl_pre_send_fn fn, void *userdata) */
/* { */
/*     ADD_HOOK(sess->pre_send_hooks, fn, userdata); */
/* } */

/* void ufwissl_hook_post_send(ufwissl_session *sess, ufwissl_post_send_fn fn, void *userdata) */
/* { */
/*     ADD_HOOK(sess->post_send_hooks, fn, userdata); */
/* } */

/* void ufwissl_hook_post_headers(ufwissl_session *sess, ufwissl_post_headers_fn fn,  */
/*                           void *userdata) */
/* { */
/*     ADD_HOOK(sess->post_headers_hooks, fn, userdata); */
/* } */

/* void ufwissl_hook_destroy_request(ufwissl_session *sess, */
/* 			     ufwissl_destroy_req_fn fn, void *userdata) */
/* { */
/*     ADD_HOOK(sess->destroy_req_hooks, fn, userdata);     */
/* } */

/* void ufwissl_hook_destroy_session(ufwissl_session *sess, */
/* 			     ufwissl_destroy_sess_fn fn, void *userdata) */
/* { */
/*     ADD_HOOK(sess->destroy_sess_hooks, fn, userdata); */
/* } */

/*
static void remove_hook(struct hook **hooks, void_fn fn, void *ud)
{
    struct hook **p = hooks;

    while (*p) {
        if ((*p)->fn == fn && (*p)->userdata == ud) {
            struct hook *next = (*p)->next;
            ufwissl_free(*p);
            (*p) = next;
            break;
        }
        p = &(*p)->next;
    }
}

#define REMOVE_HOOK(hooks, fn, ud) remove_hook(&hooks, (void_fn)fn, ud)
*/
/* void ufwissl_unhook_create_request(ufwissl_session *sess,  */
/*                               ufwissl_create_request_fn fn, void *userdata) */
/* { */
/*     REMOVE_HOOK(sess->create_req_hooks, fn, userdata); */
/* } */

/* void ufwissl_unhook_pre_send(ufwissl_session *sess, ufwissl_pre_send_fn fn, void *userdata) */
/* { */
/*     REMOVE_HOOK(sess->pre_send_hooks, fn, userdata); */
/* } */

/* void ufwissl_unhook_post_headers(ufwissl_session *sess, ufwissl_post_headers_fn fn,  */
/* 			    void *userdata) */
/* { */
/*     REMOVE_HOOK(sess->post_headers_hooks, fn, userdata); */
/* } */

/* void ufwissl_unhook_post_send(ufwissl_session *sess, ufwissl_post_send_fn fn, void *userdata) */
/* { */
/*     REMOVE_HOOK(sess->post_send_hooks, fn, userdata); */
/* } */

/* void ufwissl_unhook_destroy_request(ufwissl_session *sess, */
/*                                ufwissl_destroy_req_fn fn, void *userdata) */
/* { */
/*     REMOVE_HOOK(sess->destroy_req_hooks, fn, userdata);     */
/* } */
/*
void ufwissl_unhook_destroy_session(ufwissl_session *sess,
                               ufwissl_destroy_sess_fn fn, void *userdata)
{
    REMOVE_HOOK(sess->destroy_sess_hooks, fn, userdata);
}
*/

int ufwissl_write(ufwissl_session * session, const char *buffer, size_t count)
{
	int ret;

	if (!session)
		return UFWISSL_ERROR;

	ret = ufwissl_sock_fullwrite(session->socket, buffer, count);
	if (ret < 0)
		ufwissl_set_error(session, "%s",
				ufwissl_sock_error(session->socket));

	return ret;
}

ssize_t ufwissl_read_available(ufwissl_session * session)
{
	return ufwissl_sock_read_available(session->socket);
}

ssize_t ufwissl_read(ufwissl_session * session, char *buffer, size_t count)
{
	int ret;

	if (!session)
		return UFWISSL_ERROR;

	ret = ufwissl_sock_read(session->socket, buffer, count);
	if (ret < 0)
		ufwissl_set_error(session, "%s",
				ufwissl_sock_error(session->socket));

	return ret;
}

int ufwissl_ssl_set_keypair(ufwissl_session * session, const char *cert_file,
			  const char *key_file)
{
	ufwissl_ssl_client_cert *cert;
	int ret;
	struct stat key_stat;

	if (!session)
		return UFWISSL_ERROR;

	/* Try opening the keys */
	if (stat(key_file, &key_stat) != 0) {
		ufwissl_set_error(session,
				_("Unable to open private key %s: %s"),
				key_file, strerror(errno));
		return UFWISSL_ERROR;
	}


	if (check_key_perms(key_file) != UFWISSL_OK) {
		ufwissl_set_error(session,
				_("Permissions on private key %s are not restrictive enough, file should not be readable or writable by others."),
				key_file);
		return UFWISSL_ERROR;
	}

	cert = ufwissl_ssl_import_keypair(cert_file, key_file);
	if (cert == NULL) {
		ufwissl_set_error(session,
				_
				("Unable to load private key or certificate file"));
		return UFWISSL_ERROR;
	}

	ret = ufwissl_ssl_set_clicert(session, cert);
	return ret;
}

int ufwissl_ssl_set_pkcs12_keypair(ufwissl_session * session,
				 const char *pkcs12_file,
				 const char *password)
{
	struct stat key_stat;
	int ret = UFWISSL_OK;
	ufwissl_ssl_client_cert *cert;

	if (!session)
		return UFWISSL_ERROR;

	/* Try opening the keys */
	if (stat(pkcs12_file, &key_stat) != 0) {
		ufwissl_set_error(session,
				_("Unable to open private key %s: %s"),
				pkcs12_file, strerror(errno));
		return UFWISSL_ERROR;
	}


	if (check_key_perms(pkcs12_file) != UFWISSL_OK) {
		ufwissl_set_error(session,
				_("Permissions on private key %s are not restrictive enough, file should not be readable or writable by others."),
				pkcs12_file);
		return UFWISSL_ERROR;
	}

	cert = ufwissl_ssl_clicert_read(pkcs12_file);

	if (cert == NULL) {
		ufwissl_set_error(session,
				_
				("Unable to load PKCS12 certificate file"));
		return UFWISSL_ERROR;
	}

	if (ufwissl_ssl_clicert_encrypted(cert)) {
		if (password) {
			if (ufwissl_ssl_clicert_decrypt(cert, password) != 0) {
				ufwissl_set_error(session,
						_
						("Bad password to decrypt the PKCS key"));
				return UFWISSL_ERROR;
			}
		} else {
			ufwissl_set_error(session,
					_
					("PKCS12 file is encrypted, please supply a password"));
			return UFWISSL_ERROR;
		}
	} else {
		if (password)
			fprintf(stderr,
				"Warning, the key is not encrypted, but a password was supplied\n");
	}

	ret = ufwissl_ssl_set_clicert(session, cert);
	return ret;
}

int ufwissl_session_getpeer(ufwissl_session * sess, struct sockaddr *addr,
			  socklen_t * addrlen)
{
	int fd;
	int ret;

	if (!sess)
		return UFWISSL_ERROR;

	fd = ufwissl_session_get_fd(sess);
	memset(addr, 0, *addrlen);
	ret = getpeername(fd, addr, addrlen);

	if (ret == -1) {
		ufwissl_set_error(sess, "%s", strerror(errno));
		return UFWISSL_ERROR;
	}

	return UFWISSL_OK;
}

void *ufwissl_get_socket(ufwissl_session * sess)
{
	if (!sess)
		return NULL;

	return ufwissl__sock_sslsock(sess->socket);
}

int ufwissl_init()
{
	return ufwissl_sock_init();
}

/** @} */
