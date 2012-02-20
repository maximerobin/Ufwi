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

/**
 * \defgroup libufwiclient Libufwiclient
 * @{
 */

/*! \file libufwiclient.c
 * \brief Main file for libufwiclient
 *
 * It contains all the exported functions
 * */

/**
 * Use gcry_malloc_secure() to disallow a memory page
 * to be moved to the swap
 */
#define USE_GCRYPT_MALLOC_SECURE

#include "libufwiclient.h"
#include "ufwiclient.h"
#include "ufwi_source.h"
#include "ufwiclient_plugins.h"

#include <sasl/sasl.h>
#include <sasl/saslutil.h>
#include <stdarg.h>		/* va_list, va_start, ... */
#include <langinfo.h>
#include <proto.h>
#include "security.h"
#include "sys_config.h"
#include "internal.h"
#include "tcptable.h"
#include <sys/utsname.h>

#include <ufwissl.h>
#include <ufwibase.h>


void nu_exit_clean(nuauth_session_t * session)
{
	if (session->ct) {
		tcptable_free(session->ct);
	}

	if (session->ufwissl) {
		ufwissl_session_destroy(session->ufwissl);
		session->ufwissl = NULL;
	}

	secure_str_free(session->username);
	secure_str_free(session->password);

	free(session);
}

/**
 * \defgroup ufwiclientAPI API of libufwiclient
 * \brief The high level API of libufwiclient can be used to build a NuFW client
 *
 * A client needs to call a few functions in the correct order to be able to authenticate:
 *  - nu_client_global_init(): To be called once at program start
 *  - nu_client_new() or nu_client_new_callback(): start user session
 *  - nu_client_setup_tls(): (optionnal) setup TLS key/certificate files
 *  - nu_client_connect(): try to connect to nuauth server
 *  - nu_client_check(): check if there is packet to authenticate and send authentication
 *  request to nuauth if needed. It has to be run in a endless loop.
 *  - nu_client_delete(): free a user session
 *  - nu_client_global_deinit(): To be called once at program end
 *
 * On error, don't forget to delete session with nu_client_delete()
 */

/**
 * \ingroup ufwiclientAPI
 * \brief Destroy a client session: free all used memory
 *
 * This destroy a session and free all related structures.
 *
 * \param session A ::nuauth_session_t session to be cleaned
 */
void nu_client_delete(nuauth_session_t * session)
{
	ask_session_end(session);
	/* destroy session */
	nu_exit_clean(session);
}

/**
 * \ingroup ufwiclientAPI
 * \brief global initialisation function
 *
 * This function inits all library needed to initiate a connection to a nuauth server
 *
 * \param err A pointer to a ::ufwiclient_error_t which contains at exit the error
 *
 * \warning To be called only once.
 */
int nu_client_global_init(ufwiclient_error_t * err)
{
	int ret;
	prg_cache_init();

	if (ufwissl_init() != UFWISSL_OK)
	{
		SET_ERROR(err, INTERNAL_ERROR, UFWISSL_INIT_ERR); /* TODO: patch ufwissl to handle errors correctly in ufwissl_sock_init */
		return 0;
	}

	/* initialize the sasl library */
	ret = sasl_client_init(NULL);
	if (ret != SASL_OK) {
		SET_ERROR(err, SASL_ERROR, ret);
		return 0;
	}
	/* get local charset */
	nu_locale_charset = nl_langinfo(CODESET);
	if (nu_locale_charset == NULL) {
		fprintf(stderr, "Can't get locale charset!\n");
		return 0;
	}

	/* init capabilities string */
	ret = snprintf(nu_capabilities, NU_CAPABILITIES_MAXLENGTH, "%s", NU_CAPABILITIES);
	if (ret <= 0) {
		return 0;
	}

	INIT_LLIST_HEAD(&nu_postauth_extproto_l);
	INIT_LLIST_HEAD(&nu_cruise_extproto_l);

	init_plugins();

	return 1;
}

/**
 * \ingroup ufwiclientAPI
 * \brief Initialization: load config file
 *
 * This function loads the config file, and must be called after nu_client_global_init()
 *
 * \warning To be called only once.
 */
int nu_client_init_config()
{
	load_sys_config();

	return 1;
}

/**
 * \ingroup ufwiclientAPI
 * \brief Initialization: load plugins
 *
 * This function loads the plugins, and must be called after nu_client_global_init() and nu_client_init_config
 *
 * \warning To be called only once.
 */
int nu_client_init_plugins()
{
	load_plugins();

	return 1;
}

/**
 * \ingroup ufwiclientAPI
 * \brief  Global de init function
 *
 * \warning To be called once, when leaving.
 */
void nu_client_global_deinit()
{
	sasl_done();
}

/**
 * \ingroup ufwiclientAPI
 * \brief Set username
 *
 */
void nu_client_set_username(nuauth_session_t *session,
			    const char *username)
{
	char *utf8username = nu_client_to_utf8(username, nu_locale_charset);
	session->username = secure_str_copy(utf8username);
	free(utf8username);
}

/**
 * \ingroup ufwiclientAPI
 * \brief Set password
 *
 */
void nu_client_set_password(nuauth_session_t *session,
				    const char *password)
{
	char *utf8pass = nu_client_to_utf8(password, nu_locale_charset);
	session->password = secure_str_copy(utf8pass);
	free(utf8pass);
}

void nu_client_set_debug(nuauth_session_t * session, unsigned char enabled);

/**
 * \ingroup ufwiclientAPI
 * Get user home directory
 *
 * \return A string that need to be freed
 */

char *nu_get_home_dir()
{
	uid_t uid;
	struct passwd *pwd;
	char *dir = NULL;

	uid = getuid();
	if (!(pwd = getpwuid(uid))) {
		log_printf(DEBUG_LEVEL_CRITICAL, "Unable to get password file record");
		endpwent();
		return NULL;
	}
	dir = strdup(pwd->pw_dir);
	endpwent();
	return dir;
}

/**
 * \ingroup ufwiclientAPI
 * Get user name
 *
 * \return A string that need to be freed
 */

char *nu_get_user_name()
{
	uid_t uid;
	struct passwd *pwd;
	char *name = NULL;

	uid = getuid();
	if (!(pwd = getpwuid(uid))) {
		log_printf(DEBUG_LEVEL_CRITICAL,"Unable to get password file record");
		endpwent();
		return NULL;
	}
	name = strdup(pwd->pw_name);
	endpwent();
	return name;
}

/**
 * \ingroup ufwiclientAPI
 * Add capability to the list of supported capabilities
 *
 * \return 0 if ok, < 0 if not
 */

static int _nu_client_set_capability(char *pcapa, const char *capa)
{
	strncat(pcapa, ";", NU_CAPABILITIES_MAXLENGTH - strlen(pcapa));
	strncat(pcapa, capa, NU_CAPABILITIES_MAXLENGTH - strlen(pcapa));

	return 0;
}

/**
 * \ingroup ufwiclientAPI
 * Remove capability from the list of supported capabilities
 *
 * \return 0 if ok, < 0 if not
 */

static int _nu_client_unset_capability(char *pcapa, const char *capa)
{
	char * start, * end;
	start = strstr(pcapa, capa);
	if (start == NULL) {
		return -ENOSTR;
	}
	end = strstr(start, ";");
	*(start - 1) = '\0';
	if (end != NULL) {
		strcat(pcapa, end);
	}
	return 0;
}

int nu_client_set_capability(const char *capa)
{
	return _nu_client_set_capability(nu_capabilities, capa);
}

int nu_client_unset_capability(const char *capa)
{
	return _nu_client_unset_capability(nu_capabilities, capa);
}

int nu_client_set_session_capability(nuauth_session_t *session, const char *capa)
{
	if (session->nu_capabilities[0] == 0) {
		strcpy(session->nu_capabilities, nu_capabilities);
	}
	return _nu_client_set_capability(session->nu_capabilities, capa);
}

int nu_client_unset_session_capability(nuauth_session_t *session, const char *capa)
{
	return _nu_client_unset_capability(session->nu_capabilities, capa);
}

void nu_client_set_sasl_mechlist(nuauth_session_t * session, const char *mechlist)
{
	if (mechlist)
		session->sasl_mechlist = strdup(mechlist);
}


void nu_client_set_client_info(nuauth_session_t *session,
		const char *client_name, const char *client_version)
{
	if (client_name)
		session->client_name = strdup(client_name);

	if (client_version)
		session->client_version = strdup(client_version);
}

int nu_client_set_key(nuauth_session_t* session, const char* keyfile, const char* certfile, ufwiclient_error_t* err)
{
	if (session->pem_key)
		free(session->pem_key);

	if (session->pem_cert)
		free(session->pem_cert);

	if (keyfile)
	{
		session->pem_key = strdup(keyfile);
		log_printf(DEBUG_LEVEL_DEBUG, "Using key: %s", keyfile);
	}

	if (certfile)
	{
		session->pem_cert = strdup(certfile);
		log_printf(DEBUG_LEVEL_DEBUG, "Using certificate: %s", certfile);
	}

	return 1;
}

int nu_client_set_ca(nuauth_session_t* session, const char* cafile, ufwiclient_error_t* err)
{
	if (session->pem_ca)
		free(session->pem_ca);

	if (cafile)
		session->pem_ca = strdup(cafile);

	log_printf(DEBUG_LEVEL_DEBUG, "Using CA: %s", cafile);
	return 1;
}

int nu_client_set_pkcs12(nuauth_session_t* session, char* key_file, char* key_password, ufwiclient_error_t* err)
{
	if (session->pkcs12_file)
		free(session->pkcs12_file);

	if (session->pkcs12_password)
		free(session->pkcs12_password);

	if (key_file)
	{
		log_printf(DEBUG_LEVEL_DEBUG, "Using key: %s", key_file);
		session->pkcs12_file = strdup(key_file);
	}

	if (key_password)
		session->pkcs12_password = strdup(key_password);

	return 1;
}
/**
 * \ingroup ufwiclientAPI
 * Initialize TLS:
 *    - Set key filename (and test if the file does exist)
 *    - Set certificate (if key and cert. are present)
 *
 * \param session Pointer to client session
 * \param keyfile Complete path to a key file stored in PEM format (can be NULL)
 * \param certfile Complete path to a certificate file stored in PEM format (can be NULL)
 * \param err Pointer to a ufwiclient_error_t: which contains the error
 * \return Returns 0 on error (error description in err), 1 otherwise
 */
int nu_client_load_key(nuauth_session_t * session,
			const char *keyfile, const char *certfile,
			ufwiclient_error_t * err)
{
	char certstring[256];
	char keystring[256];
	char *home = nu_get_home_dir();
	int exit_on_error = 0;
	int ret;

	/* If the user specified a certficate and a key on command line,
	 * exit if we fail loading them.
	 * Elsewise, try loading certs from ~/.nufw/, but continue if we fail
	 */
	if (certfile || keyfile)
		exit_on_error = 1;

	/* compute patch keyfile */
	if (keyfile == NULL && home != NULL) {
		ret = secure_snprintf(keystring, sizeof(keystring),
				     "%s/.nufw/key.pem", home);
		if (ret)
			keyfile = keystring;
	}

	if (certfile == NULL && home != NULL) {
		ret = secure_snprintf(certstring, sizeof(certstring),
				     "%s/.nufw/cert.pem", home);
		if (ret)
			certfile = certstring;
	}

	if (certfile != NULL || keyfile != NULL) {
		ret = ufwissl_ssl_set_keypair(session->ufwissl, certfile, keyfile);

		if (ret != UFWISSL_OK) {
			if (exit_on_error) {
				if (home)
					free(home);
				SET_ERROR(err, UFWISSL_ERR, ret);
				return 0;
			}
			else {
				log_printf(DEBUG_LEVEL_WARNING, "Warning: Failed to load default certificate and key.");
			}
		}
	}

	if (home)
		free(home);

	return 1;
}


/**
 * \ingroup ufwiclientAPI
 * Initialize TLS:
 *    - Set PKCS12 key/certificate filename (and test if the file does exist)
 *    - Set PKCS12 password
 *
 * \param session Pointer to client session
 * \param pkcs12file Complete path to a key and a certificate file stored in PEM format (can be NULL)
 * \param pkcs12password Password of the pkcs12 file
 * \param err Pointer to a ufwiclient_error_t: which contains the error
 * \return Returns 0 on error (error description in err), 1 otherwise
 */
int nu_client_load_pkcs12(nuauth_session_t * session,
			char *pkcs12file, char *pkcs12password,
			ufwiclient_error_t * err)
{
	int ret = ufwissl_ssl_set_pkcs12_keypair(session->ufwissl, pkcs12file, pkcs12password);
	if (ret != UFWISSL_OK)
	{
		SET_ERROR(err, UFWISSL_ERR, ret);
		return 0;
	}
	return 1;
}


/**
 * \ingroup ufwiclientAPI
 * Initialize TLS:
 *    - Set trust file of credentials (if needed)
 *
 * \param session Pointer to client session
 * \param cafile Complete path to a certificate authority file stored in PEM format (can be NULL)
 * \param err Pointer to a ufwiclient_error_t: which contains the error
 * \return Returns 0 on error (error description in err), 1 otherwise
 */
int nu_client_load_ca(nuauth_session_t * session,
			const char *cafile,
			ufwiclient_error_t * err)
{
	char castring[256];
	char *home = nu_get_home_dir();
	int exit_on_error = 0;
	int ret;

	if (cafile != NULL)
		exit_on_error = 1;

	if (cafile == NULL && home != NULL) {
		ret = secure_snprintf(castring, sizeof(castring),
				     "%s/.nufw/cacert.pem", home);
		if (ret)
			cafile = castring;
	}

	if (cafile != NULL) {
		ret = ufwissl_ssl_trust_cert_file(session->ufwissl, cafile);
		if (ret != UFWISSL_OK) {
			if (exit_on_error) {
				if (home)
					free(home);
				SET_ERROR(err, UFWISSL_ERR, ret);
				return 0;
			}
			else {
				if (!session->suppress_ca_warning) {
					log_printf(DEBUG_LEVEL_WARNING, "\nWARNING: you have not provided any certificate authority.\n"
							"nutcpc will *NOT* verify server certificate trust.\n"
							"Use the -A <cafile> option to set up CA.\n"
					       );
				}
				session->suppress_fqdn_verif = 1;
				ufwissl_set_session_flag(session->ufwissl, UFWISSL_SESSFLAG_IGNORE_ID_MISMATCH, 1);
			}
		}
	} else {
		log_printf(DEBUG_LEVEL_WARNING, "Could not load any CA !");
		return 0;
	}
	return 1;
}

int nu_client_load_crl(nuauth_session_t *session, const char *crlfile,
	const char *cafile, ufwiclient_error_t * err)
{
	int ret;
	if (crlfile && *crlfile) {
		ret = ufwissl_ssl_set_crl_file(session->ufwissl, crlfile, cafile);
		if (ret != UFWISSL_OK) {
			log_printf(DEBUG_LEVEL_WARNING,"TLS error with CRL: %s",
				ufwissl_get_error(session->ufwissl));
			return 0;
		}
		log_printf(DEBUG_LEVEL_DEBUG, "Using crl: %s", crlfile);
	}
	return 1;
}

/**
 * \ingroup ufwiclientAPI
 * Returns a formatted string containing information about the TLS cipher
 * used for the connection to the server.
 *
 * \param session Pointer to client session
 * \return
 */
char* nu_client_get_cipher(nuauth_session_t * session)
{
	char buf[256];
	int ret;

	ret = ufwissl_session_get_cipher(session->ufwissl, buf, sizeof(buf));
	return (ret==0) ? strdup(buf) : NULL;
}

/**
 * \ingroup ufwiclientAPI
 * Returns a formatted string containing information about the user certificate
 *
 * \param session Pointer to client session
 * \return
 */
char* nu_client_get_cert_info(nuauth_session_t * session)
{
	return ufwissl_get_cert_info(session->ufwissl);
}


/**
 * \ingroup ufwiclientAPI
 * Returns a formatted string containing information about the server certificate
 *
 * \param session Pointer to client session
 * \return
 */
char* nu_client_get_server_cert_info(nuauth_session_t * session)
{
	return ufwissl_get_server_cert_info(session->ufwissl);
}


/**
 * \ingroup ufwiclientAPI
 */
int nu_client_set_nuauth_cert_dn(nuauth_session_t * session,
				char *nuauth_cert_dn,
				ufwiclient_error_t *err)
{
	if (*nuauth_cert_dn) {
		session->nuauth_cert_dn = nuauth_cert_dn;
	}
	return 1;
}

 /**
  * \ingroup ufwiclientAPI
  */
int nu_client_set_crlfile(nuauth_session_t * session,
		const char *crlfile,
		ufwiclient_error_t *err)
{
	if (session->pem_crl)
		free(session->pem_crl);

	if (crlfile)
		session->pem_crl = strdup(crlfile);

	return 1;
}

/**
 * \ingroup ufwiclientAPI
 */
int nu_client_set_krb5_service(nuauth_session_t * session,
				char *service)
{
	if (service) {
		session->krb5_service = service;
	}
	return 1;
}

/**
 * \ingroup ufwiclientAPI
 */
int nu_client_set_ca_suppress_warning(nuauth_session_t * session,
				int suppress_ca_warning)
{
	session->suppress_ca_warning = suppress_ca_warning;
	return 1;
}

/**
 * \ingroup ufwiclientAPI
 */
int nu_client_set_fqdn_suppress_verif(nuauth_session_t * session,
				int suppress_fqdn_verif)
{
	session->suppress_fqdn_verif = suppress_fqdn_verif;
	return 1;
}

/**
 * \ingroup ufwiclientAPI
 */
int nu_client_set_cert_suppress_verif(nuauth_session_t * session,
				int suppress_cert_verif)
{
	session->suppress_cert_verif = suppress_cert_verif;
	if (suppress_cert_verif)
		session-> suppress_fqdn_verif = 1;
	return 1;
}

/**
 * \ingroup ufwiclientAPI
 * Set IP source of the socket used to connect to nuauth server
 *
 * \param session Pointer to client session
 * \param addr Address of the socket
 */
void nu_client_set_source(nuauth_session_t *session, struct sockaddr_storage *addr)
{
	session->has_src_addr = 1;
	session->src_addr = *addr;
}

/**
 * \brief Init connection to nuauth server
 *
 * (very secure but initialization is slower)
 * \param err Pointer to a ufwiclient_error_t: which contains the error
 * \return A pointer to a valid ::nuauth_session_t structure or NULL if init has failed
 *
 * \par Internal
 * Initialisation of nufw authentication session:
 *    - set basic fields and then ;
 *    - allocate x509 credentials ;
 *    - generate Diffie Hellman params.
 *
 * If everything is ok, create the connection table using tcptable_init().
 */
nuauth_session_t *_nu_client_new(ufwiclient_error_t * err)
{
	conntable_t *new;
	nuauth_session_t *session;

	/* First reset error */
	SET_ERROR(err, INTERNAL_ERROR, NO_ERR);

	/* Allocate a new session */
	session = (nuauth_session_t *) calloc(1, sizeof(nuauth_session_t));
	if (session == NULL) {
		SET_ERROR(err, INTERNAL_ERROR, MEMORY_ERR);
		return NULL;
	}

	/* Set basic fields */
	session->userid = getuid();
	session->connected = 0;
	session->auth_by_default = 1;
	session->packet_seq = 0;
	session->ct = NULL;
	session->debug_mode = 0;
	session->verbose = 1;
	session->timestamp_last_sent = time(NULL);
	session->min_sleep_delay.tv_sec = MIN_DELAY_SEC;
	session->min_sleep_delay.tv_usec = MIN_DELAY_USEC;
	session->max_sleep_delay.tv_sec = MAX_DELAY_SEC;
	session->max_sleep_delay.tv_usec = MAX_DELAY_USEC;
	session->sleep_delay.tv_sec = MIN_DELAY_SEC;
	session->sleep_delay.tv_usec = MIN_DELAY_USEC;
	session->hash = 0;

	if (tcptable_init(&new) == 0) {
		SET_ERROR(err, INTERNAL_ERROR, MEMORY_ERR);
		nu_exit_clean(session);
		return NULL;
	}
	session->ct = new;

	nu_client_set_client_info(session, "unknown client", "unknown version");

	return session;
}

/**
 * \ingroup ufwiclientAPI
 * \brief Create new session and use callbacks.
 *
 * Callbacks are used to fetch username and password if they are
 * necessary for SASL negotiation.
 *
 * \param username_callback User name retrieving callback
 * \param passwd_callback Password retrieving callback
 * \param diffie_hellman If equals to 1, use Diffie Hellman for key exchange
 * (very secure but initialization is slower)
 * \param err Pointer to a ufwiclient_error_t: which contains the error
 * \return A pointer to a valid ::nuauth_session_t structure or NULL if init has failed
 */

nuauth_session_t *nu_client_new_callback(void *username_callback,
		      void *passwd_callback,
		      unsigned char diffie_hellman, ufwiclient_error_t * err)
{
	nuauth_session_t *session = NULL;

	if (username_callback == NULL || passwd_callback == NULL) {
		SET_ERROR(err, INTERNAL_ERROR, BAD_CREDENTIALS_ERR);
		return NULL;
	}

	session = _nu_client_new(err);

	session->username_callback = username_callback;
	session->passwd_callback = passwd_callback;

	return session;
}

/**
 * \ingroup ufwiclientAPI
 * \brief Create new session.
 *
 * This function has to be used to create a new ::nuauth_session_t if there
 * is no plan to use a callback for getting username or password.
 *
 * \param username User name string
 * \param password Password string
 * \param diffie_hellman If equals to 1, use Diffie Hellman for key exchange
 * (very secure but initialization is slower)
 * \param err Pointer to a ufwiclient_error_t: which contains the error
 * \return A pointer to a valid ::nuauth_session_t structure or NULL if init has failed
 */

nuauth_session_t *nu_client_new(const char *username,
		      const char *password,
		      unsigned char diffie_hellman, ufwiclient_error_t * err)
{
	nuauth_session_t *session = NULL;

	if (username == NULL || password == NULL) {
		SET_ERROR(err, INTERNAL_ERROR, BAD_CREDENTIALS_ERR);
		return NULL;
	}

	session = _nu_client_new(err);

	session->username = secure_str_copy(username);
	session->password = secure_str_copy(password);
	session->nu_capabilities[0] = 0;
	if (session->username == NULL || session->password == NULL) {
		SET_ERROR(err, INTERNAL_ERROR, MEMORY_ERR);
		return NULL;
	}

	return session;
}

/**
 * \ingroup ufwiclientAPI
 * Reset a session: close the connection and reset attributes. So the session
 * can be used as nu_client_connect() input.
 */
void nu_client_reset(nuauth_session_t * session)
{
	ask_session_end(session);

	/* reset fields */
	session->connected = 0;
	session->timestamp_last_sent = time(NULL);
}

static int finish_init(nuauth_session_t * session, ufwiclient_error_t * err)
{
	int finish = 0;
	int ret;
	char buf[1024];
	int bufsize;
	struct nu_srv_message * message = (struct nu_srv_message *) buf;

	while (! finish) {
		bufsize = ufwissl_read(session->ufwissl, buf, sizeof(buf));
		if ((bufsize <= 0) ||
			((size_t)bufsize < sizeof(struct nu_srv_message))) {
			/* allo houston */
			return 0;
		}
		switch (message->type) {
			case SRV_REQUIRED_INFO:
				switch (message->option) {
					case OS_VERSION:
						if (!send_os(session, err)) {
							return 0;
						}
						break;
					case CLIENT_VERSION:
						if (!send_client(session, err)) {
							return 0;
						}
						break;
					case CLIENT_CAPA:
						if (!send_capa(session, err)) {
							return 0;
						}
						break;
					default:
						return 0;
				}
				break;
			case SRV_TYPE:
				switch (message->option) {
					case SRV_TYPE_POLL:
					case SRV_TYPE_PUSH:
						session->server_mode = message->option;
						break;
					case SRV_HASH_TYPE:
						session->hash = ntohs(message->length);
						break;
					default:
						break;
				}
				break;
			case SRV_EXTENDED_PROTO:
				ret = process_ext_message(buf + sizeof(struct nu_srv_message),
						bufsize - sizeof(struct nu_srv_message),
						&nu_postauth_extproto_l,
						session);
				if (ret != 0) {
					return 0;
				}
				break;
			case SRV_INIT:
				finish = 1;
				switch (message->option) {
					case INIT_NOK:
						SET_ERROR(err, INTERNAL_ERROR, NUFW_INITNEGO_ERR);
						return 0;
					case INIT_OK:
						session->connected = 1;
						break;
				}
				break;
		}
	}

	return 1;

}

/**
 * \ingroup ufwiclientAPI
 * Try to connect to nuauth server:
 *    - init_socket(): create socket to server ;
 *    - tls_handshake(): TLS handshake ;
 *    - init_sasl(): authentication with SASL ;
 *    - send_os(): send OS field.
 *
 * \param session Pointer to client session
 * \param hostname String containing hostname of nuauth server (default: #NUAUTH_IP)
 * \param service Port number (or string) on which nuauth server is listening (default: #USERPCKT_SERVICE)
 * \param err Pointer to a ufwiclient_error_t: which contains the error
 * \return Returns 0 on error (error description in err), 1 otherwise
 */
int nu_client_connect(nuauth_session_t * session,
		      const char *hostname, const char *service,
		      ufwiclient_error_t * err)
{
	int ret;
	unsigned int port = atoi(service);

	session->ufwissl = ufwissl_session_create(UFWISSL_SSL_CTX_CLIENT);

	if (session->suppress_cert_verif)
		ufwissl_ssl_disable_certificate_check(session->ufwissl,1);

	if (session->suppress_fqdn_verif)
		ufwissl_set_session_flag(session->ufwissl, UFWISSL_SESSFLAG_IGNORE_ID_MISMATCH, 1);

	ufwissl_set_hostinfo(session->ufwissl, hostname, port);
	if (session->pkcs12_file) {
		if (!nu_client_load_pkcs12(session, session->pkcs12_file, session->pkcs12_password, err))
			return 0;
	} else {
		if (!nu_client_load_key(session, session->pem_key, session->pem_cert, err))
			return 0;
	}

	if (!nu_client_load_ca(session, session->pem_ca, err))
		return 0;

	if (session->pem_crl) {
		if (!nu_client_load_crl(session, session->pem_crl, session->pem_ca, err))
			return 0;
	}

	ret = ufwissl_open_connection(session->ufwissl);
	if (ret != UFWISSL_OK) {
		log_printf(DEBUG_LEVEL_CRITICAL, "%s", ufwissl_get_error(session->ufwissl));
		ufwissl_session_destroy(session->ufwissl);
		session->ufwissl = NULL;
		SET_ERROR(err, UFWISSL_ERR, ret);
		return 0;
	}

	if (!init_sasl(session, hostname, err)) {
		plugin_emit_event(NUCLIENT_EVENT_LOGIN_FAILED, session, session->username);
		return 0;
	}

	if (!finish_init(session, err)) {
		plugin_emit_event(NUCLIENT_EVENT_LOGIN_FAILED, session, session->username);
		return 0;
	}

	plugin_emit_event(NUCLIENT_EVENT_LOGIN_OK, session, session->username);

	return 1;
}

/**
 * \ingroup ufwiclientAPI
 * Enable or disabled debug mode
 *
 * \param session Pointer to client session
 * \param enabled Enable debug if different than zero (1), disable otherwise
 */
void nu_client_set_debug(nuauth_session_t * session, unsigned char enabled)
{
	session->debug_mode = enabled;
}


/**
 * \ingroup ufwiclientAPI
 * Enable or disabled verbose mode
 *
 * \param session Pointer to client session
 * \param enabled Enable verbose mode if different than zero (1), disable otherwise
 */
void nu_client_set_verbose(nuauth_session_t * session, unsigned char enabled)
{
	session->verbose = enabled;
}

/**
 * \ingroup ufwiclientAPI
 * Set minimum delay
 *
 * \param session Pointer to client session
 * \param delay a timeval which will be equal to the minimum delay
 * between two checks (in ms)
 */
void nu_client_set_min_delay(nuauth_session_t * session, unsigned int delay)
{
	session->min_sleep_delay.tv_sec = delay / 1000;
	session->min_sleep_delay.tv_usec = (delay * 1000) % 1000000;
}

/**
 * \ingroup ufwiclientAPI
 * Set maximum delay
 *
 * \param session Pointer to client session
 * \param delay a timeval which will be equal to the maximum delay
 * between two checks (in ms)
 */
void nu_client_set_max_delay(nuauth_session_t * session, unsigned int delay)
{
	session->max_sleep_delay.tv_sec = delay / 1000;
	session->max_sleep_delay.tv_usec = (delay * 1000) % 1000000;
}

/**
 * \ingroup ufwiclientAPI
 * \brief Allocate a structure to store client error
 */
int nu_client_error_init(ufwiclient_error_t ** err)
{
	if (*err != NULL)
		return -1;
	*err = malloc(sizeof(ufwiclient_error_t));
	if (*err == NULL)
		return -1;
	return 0;
}

/**
 * \ingroup ufwiclientAPI
 * \brief Destroy an error (free memory)
 */
void nu_client_error_destroy(ufwiclient_error_t * err)
{
	if (err != NULL)
		free(err);
}

/**
 * \ingroup ufwiclientAPI
 * \brief Convert an error to an human readable string
 */
const char *nu_client_strerror(nuauth_session_t * session, ufwiclient_error_t * err)
{
	if (err == NULL) {
		return "Error structure was not initialised";
	}

	switch (err->family) {
	case UFWISSL_ERR:
		if (session == NULL || session->ufwissl == NULL)
			return "NuSSL initialization error.";
		return ufwissl_get_error(session->ufwissl);
	case SASL_ERROR:
		return sasl_errstring(err->error, NULL, NULL);
		break;
	case INTERNAL_ERROR:
		switch (err->error) {
		case NO_ERR:
			return "No error";
		case SESSION_NOT_CONNECTED_ERR:
			return "Session not connected";
		case TIMEOUT_ERR:
			return "Connection timeout";
		case DNS_RESOLUTION_ERR:
			return "DNS resolution error";
		case NO_ADDR_ERR:
			return "Address not recognized";
		case FILE_ACCESS_ERR:
			return "File access error";
		case CANT_CONNECT_ERR:
			return "Connection failed";
		case MEMORY_ERR:
			return "No more memory";
		case TCPTABLE_ERR:
			return "Unable to read connection table";
		case SEND_ERR:
			return "Unable to send packet to nuauth";
		case BAD_CREDENTIALS_ERR:
			return "Bad credentials";
		case BINDING_ERR:
			return "Binding (source address) error";
		case UFWISSL_INIT_ERR:
			return "NuSSL initialisation failed.";
		case NUFW_INITNEGO_ERR:
			return "NuFW refused connection during init.";
		case NUFW_CRUISE_ERR:
			return "NuFW error during cruise protocol.";
		case PROTO_ERR:
			return "Protocol error (too old authentication server ?).";
		default:
			return "Unknown internal error code";
		}
		break;
	default:
		return "Unknown family error";
	}
}

/**
 * \ingroup ufwiclientAPI
 * Get version of ufwiclient library (eg. "2.1.1-3")
 *
 * \return Nuclient version string
 */
const char *nu_get_version()
{
	return NUCLIENT_VERSION;
}

/**
 * \ingroup ufwiclientAPI
 * Check if libufwiclient if the specified version. Use #NUCLIENT_VERSION
 * as argument. See also function nu_get_version().
 *
 * \return Return 1 if ok, 0 if versions are different.
 */
int nu_check_version(const char *version)
{
	if (strcmp(NUCLIENT_VERSION, version) == 0)
		return 1;
	else
		return 0;
}

/** @} */
