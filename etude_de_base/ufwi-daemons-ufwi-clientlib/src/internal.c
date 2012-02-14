/*
 ** Copyright 2004-2010 - EdenWall Technologies
 ** Written by Eric Leblond <regit@inl.fr>
 **            Vincent Deffontaines <vincent@inl.fr>
 **            Pierre Chifflier <chifflier@edenwall.com>
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

#include "ufwi_source.h"
#include "libufwiclient.h"
#include "ufwiclient_plugins.h"
#include "sending.h"
#include "tcptable.h"
#include <sasl/saslutil.h>
#include <stdarg.h>		/* va_list, va_start, ... */
#include <langinfo.h>
#include <proto.h>
#include "proc.h"
#include "security.h"
#include "internal.h"
#include <sys/utsname.h>

#include <ufwissl.h>
#include <ufwibase.h>

char* nu_locale_charset;

/**
 * \ingroup libufwiclient
 * @{
 */

/**
 * Display an error message, prefixed by "Fatal error: ", and then exit the
 * program. If filename is not NULL and line different than zero, also prefix
 * the message with them.
 *
 * Example: "checks.c:45:Fatal error: Message ..."
 */
void do_panic(const char *filename, unsigned long line, const char *fmt,
	      ...)
{
	va_list args;
	va_start(args, fmt);
	printf("\n");
	if (filename != NULL && line != 0) {
		printf("%s:%lu:", filename, line);
	}
	printf("Fatal error: ");
	vprintf(fmt, args);
	printf("\n");
	fflush(stdout);
	exit(EXIT_FAILURE);
	va_end(args);
}


static int samp_send(nuauth_session_t* session, const char *buffer,
		     unsigned length, ufwiclient_error_t * err)
{
	char *buf;
	unsigned len, alloclen;
	int result;

	/* prefix ("C: ") + base64 length + 1 nul byte */
	alloclen = 3 + ((length+2)/3)*4 + 1;
	buf = malloc(alloclen);
	if (buf == NULL) {
		SET_ERROR(err, INTERNAL_ERROR, MEMORY_ERR);
		return 0;
	}

	result = sasl_encode64(buffer, length, buf + 3, alloclen - 3, &len);
	if (result != SASL_OK) {
		SET_ERROR(err, SASL_ERROR, result);
		free(buf);
		return 0;
	}

	memcpy(buf, "C: ", 3);

	result = ufwissl_write(session->ufwissl, buf, len + 3);
	if (result < 0) {
		SET_ERROR(err, UFWISSL_ERR, result);
		free(buf);
		return 0;
	}

	free(buf);
	return 1;
}


/* XXX: Move this fuction into ufwissl */
static unsigned samp_recv(nuauth_session_t* session, char *buf, int bufsize,
			  ufwiclient_error_t * err)
{
	unsigned len;
	int result;
	int tls_len;

	tls_len = ufwissl_read(session->ufwissl, buf, bufsize);
	if (tls_len <= 0) {
		log_printf(DEBUG_LEVEL_CRITICAL, "ERROR ufwissl_read returned %d (requested %d bytes)", tls_len, bufsize);
		SET_ERROR(err, UFWISSL_ERR, tls_len);
		return 0;
	}

	result = sasl_decode64(buf + 3, (unsigned) strlen(buf + 3), buf,
			       bufsize, &len);
	if (result != SASL_OK) {
		log_printf(DEBUG_LEVEL_CRITICAL, "ERROR sasl_decode64 returned %d", result);
		SET_ERROR(err, SASL_ERROR, result);
		return 0;
	}
	buf[len] = '\0';
	return len;
}



int mysasl_negotiate(nuauth_session_t * session, sasl_conn_t * conn,
		     ufwiclient_error_t * err)
{
	char buf[8192];
	const char *data;
	const char *mechlist = session->sasl_mechlist;
	const char *chosenmech;
	unsigned len;
	int result;
	int retry_auth = 1;
	/* gnutls_session session = session->tls; */

	memset(buf, 0, sizeof buf);
	/* get the capability list */
	len = samp_recv(session, buf, 8192, err);
	if (len == 0) {
		return SASL_FAIL;
	}

	if (mechlist == NULL)
		mechlist = buf;

	while (retry_auth > 0) {
		retry_auth--;

		if (session->verbose) {
			log_printf(DEBUG_LEVEL_DEBUG, "Server mechanisms %s", buf);
			log_printf(DEBUG_LEVEL_DEBUG, "Client mechanisms %s", mechlist);
		}

		result = sasl_client_start(conn,
					   mechlist, NULL, &data, &len, &chosenmech);
		if (result == -1 && strcasestr(mechlist, "gssapi") != NULL) {
			log_printf(DEBUG_LEVEL_WARNING, "SASL negotiation with mechanism %s failed, retrying with PLAIN", chosenmech);
			mechlist = "PLAIN";
			retry_auth = 1;
		}
	}

	if (session->verbose) {
		log_printf(DEBUG_LEVEL_INFO, "Using mechanism %s", chosenmech);
	}

	if (result != SASL_OK && result != SASL_CONTINUE) {
		if (session->verbose) {
			log_printf(DEBUG_LEVEL_CRITICAL, "Error starting SASL negotiation");
			log_printf(DEBUG_LEVEL_CRITICAL, "\n%s\n", sasl_errdetail(conn));
		}
		SET_ERROR(err, SASL_ERROR, result);
		return SASL_FAIL;
	}

	strcpy(buf, chosenmech);
	if (data) {
		if (8192 - strlen(buf) - 1 < len) {
			return SASL_FAIL;
		}
		memcpy(buf + strlen(buf) + 1, data, len);
		len += (unsigned) strlen(buf) + 1;
		data = NULL;
	} else {
		len = (unsigned) strlen(buf);
	}

	if (!samp_send(session, buf, len, err)) {
		return SASL_FAIL;
	}

	while (result == SASL_CONTINUE) {
		if (session->verbose) {
			log_printf(DEBUG_LEVEL_DEBUG, "Waiting for server reply...");
		}
		memset(buf, 0, sizeof(buf));
		len = samp_recv(session, buf, sizeof(buf), err);
		if (len <= 0) {
			log_printf(DEBUG_LEVEL_CRITICAL, "server problem, recv fail...");
			return SASL_FAIL;
		}
		result =
		    sasl_client_step(conn, buf, len, NULL, &data, &len);
		if (result != SASL_OK && result != SASL_CONTINUE) {
			if (session->verbose)
				log_printf(DEBUG_LEVEL_DEBUG, "Performing SASL negotiation");
			SET_ERROR(err, SASL_ERROR, result);
		}
		if (data && len) {
			if (session->verbose)
				puts("Sending response...\n");
			if (!samp_send(session, data, len, err)) {
				return SASL_FAIL;
			}
		} else if (result != SASL_OK) {
			if (!samp_send(session, "", 0, err)) {
				return SASL_FAIL;
			}
		}
	}

	len = samp_recv(session, buf, 42, err);
	if (buf[0] != 'Y') {
		result = SASL_BADAUTH;
		SET_ERROR(err, SASL_ERROR, SASL_BADAUTH);
	}

	if (result != SASL_OK) {
		if (session->verbose)
			puts("Authentication failed...");
		return SASL_FAIL;
	} else {
		if (session->verbose)
			puts("Authentication started...");
	}

	return SASL_OK;
}

int add_packet_to_send(nuauth_session_t * session, conn_t ** auth,
			      int *count_p, conn_t * bucket)
{
	int count = *count_p;
	if (count < CONN_MAX - 1) {
		auth[count] = bucket;
		(*count_p)++;
	} else {
		int i;
		auth[count] = bucket;
		if (send_user_pckt(session, auth) != 1) {
			/* error sending */
#if DEBUG
			log_printf(DEBUG_LEVEL_CRITICAL, "error when sending");
#endif

			return -1;
		}
		for (i = 0; i < CONN_MAX; i++) {
			auth[i] = NULL;
		}
		*count_p = 0;
	}
	return 1;
}

/**
 * \brief Compare connection tables and send packets
 *
 * Compare the `old' and `new' tables, sending packet to nuauth
 * if differences are found.
 *
 * \return -1 if error (then disconnect is needed) or the number of
 * authenticated packets if it has succeeded
 */
int compare(nuauth_session_t * session, conntable_t * old, conntable_t * new,
	    ufwiclient_error_t * err)
{
	int i;
	int count = 0;
	conn_t *auth[CONN_MAX];
	int nb_packets = 0;

	assert(old != NULL);
	assert(new != NULL);
	for (i = 0; i < CONNTABLE_BUCKETS; i++) {
		conn_t *bucket;
		conn_t *same_bucket;

		bucket = new->buckets[i];
		while (bucket != NULL) {
			same_bucket = tcptable_find(old, bucket);
			if (same_bucket == NULL) {
#if DEBUG
				log_printf(DEBUG_LEVEL_DEBUG, "sending new");
#endif
#ifdef LINUX
				prg_cache_load();
#endif
				if (add_packet_to_send
				    (session, auth, &count,
				     bucket) == -1) {
					/* problem when sending we exit */
					return -1;
				}
				plugin_emit_event(NUCLIENT_EVENT_NEW_CONNECTION, session, (char *)bucket);
				nb_packets++;
			} else {
				/* compare values of retransmit */
				if (bucket->retransmit >
				    same_bucket->retransmit) {
#if DEBUG
					log_printf(DEBUG_LEVEL_DEBUG, "sending retransmit");
#endif
#ifdef LINUX
					prg_cache_load();
#endif

					if (add_packet_to_send
					    (session, auth, &count,
					     bucket) == -1) {
						/* problem when sending we exit */
						return -1;

					}
					plugin_emit_event(NUCLIENT_EVENT_RETRANSMIT_CONNECTION, session, (char *)bucket);
					nb_packets++;
				}

				/* solve timeout issue on UDP */
				if (bucket->protocol == IPPROTO_UDP) {
					/* send an auth packet if netfilter timeout may have been reached */
					if (same_bucket->createtime <
					    time(NULL) - UDP_TIMEOUT) {
#if DEBUG
						log_printf(DEBUG_LEVEL_DEBUG,
						    "working on timeout issue");
#endif
#ifdef LINUX
						prg_cache_load();
#endif
						if (add_packet_to_send
						    (session, auth, &count,
						     bucket) == -1) {
							return -1;
						}
						nb_packets++;
					} else {
						bucket->createtime =
						    same_bucket->
						    createtime;
					}
				}
			}
			bucket = bucket->next;
		}
	}
	if (count > 0) {
		if (count < CONN_MAX) {
			auth[count] = NULL;
		}
		if (send_user_pckt(session, auth) != 1) {
			/* error sending */
			return -1;
		}
	}
	return nb_packets;
}

/**
 * Create the operating system packet and send it to nuauth.
 * Packet is in format ::nuv2_authfield.
 *
 * \param session Pointer to client session
 * \param err Pointer to a ufwiclient_error_t: which contains the error
 */
int send_os(nuauth_session_t * session, ufwiclient_error_t * err)
{
	/* announce our OS */
	struct utsname info;
	char oses[256];
	char buf[1024];
	char *enc_oses = buf + sizeof(struct nu_authfield);
	struct nu_authfield *osfield = (struct nu_authfield *) buf;
	unsigned stringlen;
	unsigned actuallen;
	int ret;

	/* read OS informations */
	uname(&info);

	/* encode OS informations in base64 */
	stringlen = strlen(info.sysname) + 1
	    + strlen(info.release) + 1 + strlen(info.version) + 1;

	(void) secure_snprintf(oses, stringlen,
			       "%s;%s;%s",
			       info.sysname, info.release, info.version);
	if (sasl_encode64(oses, strlen(oses), enc_oses, 4 * stringlen,
	     &actuallen) == SASL_BUFOVER) {
		SET_ERROR(err, SASL_ERROR, SASL_BUFOVER);
		/* TODO set explicit string message */
		return 0;
	}

	/* build packet header */
	osfield->type = OS_FIELD;
	osfield->option = OS_SRV;
	osfield->length = sizeof(struct nu_authfield) + actuallen;

	/* add packet body */
	osfield->length = htons(osfield->length);

	/* Send OS field over network */
	ret = ufwissl_write(session->ufwissl, buf, ntohs(osfield->length));
	if (ret < 0) {
		if (session->verbose)
			log_printf(DEBUG_LEVEL_CRITICAL, "Error sending OS data: %s",
					ufwissl_get_error(session->ufwissl));
		SET_ERROR(err, UFWISSL_ERR, ret);
		return 0;
	}

	return 1;
}

/**
 * Create the client information packet and send it to nuauth.
 * Packet is in format ::nuv2_authfield.
 *
 * \param session Pointer to client session
 * \param err Pointer to a ufwiclient_error_t: which contains the error
 */
int send_client(nuauth_session_t * session, ufwiclient_error_t * err)
{
	char version[256];
	char buf[1024];
	struct nu_authfield *vfield = (struct nu_authfield *) buf;
	char *enc_version = buf + sizeof(struct nu_authfield);
	unsigned stringlen = 256;
	unsigned actuallen;
	int ret;

	(void) secure_snprintf(version, stringlen,
			       "%s;%s",
			       session->client_name, session->client_version);
	if (sasl_encode64(version, strlen(version), enc_version, 4 * stringlen,
	     &actuallen) == SASL_BUFOVER) {
		SET_ERROR(err, SASL_ERROR, SASL_BUFOVER);
		/* TODO set explicit string message */
		return 0;
	}

	/* build packet header */
	vfield->type = VERSION_FIELD;
	vfield->option = CLIENT_SRV;
	vfield->length = sizeof(struct nu_authfield) + actuallen;

	/* add packet body */
	vfield->length = htons(vfield->length);

	/* Send Client version field over network */
	ret = ufwissl_write(session->ufwissl, buf, ntohs(vfield->length));
	if (ret < 0) {
		if (session->verbose)
			log_printf(DEBUG_LEVEL_CRITICAL, "Error sending Client data: %s",
					ufwissl_get_error(session->ufwissl));
		SET_ERROR(err, UFWISSL_ERR, ret);
		return 0;
	}

	return 1;
}

/**
 * Create the client information packet and send it to nuauth.
 * Packet is in format ::nuv2_authfield.
 *
 * \param session Pointer to client session
 * \param err Pointer to a ufwiclient_error_t: which contains the error
 */
int send_capa(nuauth_session_t * session, ufwiclient_error_t * err)
{
	char buf[1024];
	struct nu_authfield *vfield = (struct nu_authfield *) buf;
	char *enc_capa = buf + sizeof(struct nu_authfield);
	unsigned stringlen = sizeof(nu_capabilities);
	unsigned actuallen;
	char *capa;
	int ret;

	if (session->nu_capabilities[0])
		capa = session->nu_capabilities;
	else
		capa = nu_capabilities;

	if (sasl_encode64(capa, strlen(capa), enc_capa, 4 * stringlen,
	     &actuallen) == SASL_BUFOVER) {
		SET_ERROR(err, SASL_ERROR, SASL_BUFOVER);
		/* TODO set explicit string message */
		return 0;
	}

	/* build packet header */
	vfield->type = CAPA_FIELD;
	vfield->option = CLIENT_SRV;
	vfield->length = sizeof(struct nu_authfield) + actuallen;

	/* add packet body */
	vfield->length = htons(vfield->length);

	/* Send capabilities field over network */
	ret = ufwissl_write(session->ufwissl, buf, ntohs(vfield->length));
	if (ret < 0) {
		if (session->verbose)
			log_printf(DEBUG_LEVEL_CRITICAL, "Error sending Capabilities data: %s",
					ufwissl_get_error(session->ufwissl));
		SET_ERROR(err, UFWISSL_ERR, ret);
		return 0;
	}

	return 1;
}

/**
 * SASL callback used to get password
 *
 * \return SASL_OK if ok, EXIT_FAILURE on error
 */
static int nu_get_usersecret(sasl_conn_t * conn __attribute__ ((unused)),
		      void *context __attribute__ ((unused)), int id,
		      sasl_secret_t ** psecret)
{
	size_t len;
	nuauth_session_t *session = (nuauth_session_t *) context;
	if (id != SASL_CB_PASS) {
		if (session->verbose)
			log_printf(DEBUG_LEVEL_CRITICAL, "getsecret not looking for pass");
		return SASL_BADPARAM;
	}
	if ((session->password == NULL) && session->passwd_callback) {
#if USE_UTF8
		char *utf8pass;
#endif
		char *givenpass=session->passwd_callback();
		if (!givenpass){
			return SASL_FAIL;
		}
#if USE_UTF8
		utf8pass = nu_client_to_utf8(givenpass, nu_locale_charset);
		free(givenpass);
		givenpass = utf8pass;
		if (!givenpass){
			return SASL_FAIL;
		}
#endif
		session->password = givenpass;
	}
	if (!psecret)
		return SASL_BADPARAM;

	len = strlen(session->password);
	*psecret =
	    (sasl_secret_t *) calloc(sizeof(sasl_secret_t) + len + 1,
				     sizeof(char));
	(*psecret)->len = len;
	SECURE_STRNCPY((char *) (*psecret)->data, session->password,
		       len + 1);
	return SASL_OK;
}

static int nu_get_userdata(void *context __attribute__ ((unused)),
			    int id, const char **result, unsigned *len)
{
	nuauth_session_t *session = (nuauth_session_t *) context;
	/* paranoia check */
	if (!result)
		return SASL_BADPARAM;

	switch (id) {
	case SASL_CB_USER:
	case SASL_CB_AUTHNAME:
		if ((session->username == NULL) && session->username_callback) {
#if USE_UTF8
			char *utf8name;
#endif
			char *givenuser=session->username_callback();
#if USE_UTF8
			utf8name = nu_client_to_utf8(givenuser, nu_locale_charset);
			free(givenuser);
			givenuser = utf8name;
			if (givenuser == NULL){
				return SASL_FAIL;
			}
#endif
			session->username = givenuser;
		}
		*result = session->username;
		break;
	default:
		return SASL_BADPARAM;
	}

	if (len)
		*len = strlen(*result);

	return SASL_OK;
}



/**
 * Initialize SASL: create an client, set properties
 * and then call mysasl_negotiate()
 *
 * \param session Pointer to client session
 * \param hostname Name (FQDN) of the Nuauth server
 * \param err Pointer to a ufwiclient_error_t: which contains the error
 */
int init_sasl(nuauth_session_t * session, const char *hostname, ufwiclient_error_t * err)
{
	int ret;
	sasl_conn_t *conn;
	sasl_ssf_t extssf = 0;
	char * krb5_service = NULL;
	const char * server_fqdn = hostname;
	sasl_security_properties_t secprops;
	char buffer[12];

	/* SASL time */
	sasl_callback_t callbacks[] = {
		{SASL_CB_USER, &nu_get_userdata, session},
		{SASL_CB_AUTHNAME, &nu_get_userdata, session},
		{SASL_CB_PASS, &nu_get_usersecret, session},
		{SASL_CB_LIST_END, NULL, NULL}
	};

	ret = ufwissl_write(session->ufwissl, "PROTO 6", strlen("PROTO 6"));
	if (ret < 0) {
		SET_ERROR(err, UFWISSL_ERR, ret);
		return 0;
	}

	/* wait of "OK" from server, an other chain will be a failure
	 * because we can not yet downgrade our protocol */
	ret = ufwissl_read(session->ufwissl, buffer, sizeof(buffer));
	if (ret <= 0) {
		log_printf(DEBUG_LEVEL_CRITICAL,
		           "ufwissl_read() failed: %s",
			   ufwissl_get_error(session->ufwissl));
		SET_ERROR(err, UFWISSL_ERR, ret);
		return 0;
	}
	if (strncmp("OK", buffer, 2)) {
		log_printf(DEBUG_LEVEL_CRITICAL, "received: \"%s\"", buffer);
		SET_ERROR(err, INTERNAL_ERROR, PROTO_ERR);
		return 0;
	}

	krb5_service = session->krb5_service;
	if (krb5_service == NULL)
		krb5_service = DEFAULT_KRB5_REALM;

	/* client new connection */
	ret = sasl_client_new(krb5_service, server_fqdn, NULL, NULL, callbacks, 0, &conn);
	if (ret != SASL_OK) {
		if (session->verbose)
			log_printf(DEBUG_LEVEL_CRITICAL, "Failed allocating connection state");
		errno = EAGAIN;
		SET_ERROR(err, SASL_ERROR, ret);
		return 0;
	}

	if (! session->username){
		/* set username taken from console */
		if (session->username_callback){
			session->username = session->username_callback();
		} else {
			if (session->verbose)
				log_printf(DEBUG_LEVEL_CRITICAL, "Can't call username callback");
		}
	}

	secprops.min_ssf = 0;
	secprops.max_ssf = UINT_MAX;
	secprops.property_names = NULL;
	secprops.property_values = NULL;
	secprops.security_flags = SASL_SEC_NOANONYMOUS; /* as appropriate */
	secprops.maxbufsize = 65536;
	sasl_setprop(conn, SASL_SEC_PROPS, &secprops);
	
	sasl_setprop(conn, SASL_SSF_EXTERNAL, &extssf);
	ret = sasl_setprop(conn, SASL_AUTH_EXTERNAL, session->username);
	if (ret != SASL_OK) {
		errno = EACCES;
		SET_ERROR(err, SASL_ERROR, ret);
		return 0;
	}

	ret = mysasl_negotiate(session, conn, err);
	if (ret != SASL_OK) {
		errno = EACCES;
		/*        SET_ERROR(err, SASL_ERROR, ret); */
		return 0;
	}
	sasl_dispose(&conn);

	return 1;
}

/**
 * Make a copy in a string in a secure memory buffer, ie. buffer never moved
 * to swap (hard drive). Use secure_str_free() to free the memory when you
 * don't need the string anymore.
 *
 * If USE_GCRYPT_MALLOC_SECURE compilation option in not set,
 * strdup() is used.
 *
 * \return Copy of the string, or NULL on error.
 */
char *secure_str_copy(const char *orig)
{
#ifdef USE_GCRYPT_MALLOC_SECURE
	size_t len = strlen(orig);
	char *new = gcry_calloc_secure(len + 1, sizeof(char));
	if (new != NULL) {
		SECURE_STRNCPY(new, orig, len + 1);
	}
	return new;
#else
	return strdup(orig);
#endif
}

void ask_session_end(nuauth_session_t * session)
{
	/* sanity checks */
	if (session == NULL) {
		return;
	}
	if (session->ufwissl) {
		ufwissl_session_destroy(session->ufwissl);
		session->ufwissl = NULL;
	}
	session->connected = 0;
}


/** @} */
