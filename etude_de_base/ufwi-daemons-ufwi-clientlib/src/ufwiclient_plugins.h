/*
 ** Copyright 2009 - INL
 ** Written by Pierre Chifflier <chifflier@inl.fr>
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

/*! \file ufwiclient_plugins.h
 * \brief Plugins helper functions
 *
 * */

#ifndef __NUCLIENT_PLUGINS_H__
#define __NUCLIENT_PLUGINS_H__

typedef enum {
	NUCLIENT_EVENT_NULL = 0,
	NUCLIENT_EVENT_LOGIN_OK,
	NUCLIENT_EVENT_LOGIN_FAILED,
	NUCLIENT_EVENT_NEW_CONNECTION,
	NUCLIENT_EVENT_RETRANSMIT_CONNECTION,
	NUCLIENT_EVENT_END_CHECK,

	/* never change this one, it must be the last one */
	NUCLIENT_EVENT_MAX
} plugin_event_t;


#define PLUGIN_MAGIC	0x37c00000
#define PLUGIN_API_NUM	(PLUGIN_MAGIC + \
	(sizeof(struct ufwiclient_plugin_t) << 4) + \
	(sizeof(int) << 12) + \
	NUCLIENT_EVENT_MAX)


struct ufwiclient_plugin_t;

/** \brief Signature for plugin instance init function
 *
 * Argument are:
 *   - plugin instance
 *   - (optional) arguments
 */
typedef int (*ufwiclient_plugin_instance_init_func)(struct ufwiclient_plugin_t *, void *args);

/** \brief Signature for plugin dispatch function
 *
 * Argument are:
 *   - event id
 *   - nuauth session
 *   - (optional) arguments
 */
typedef int (*ufwiclient_plugin_dispatch_func)(struct ufwiclient_plugin_t *, unsigned int, nuauth_session_t *, const char*);

/** \brief Signature for plugin close function
 */
typedef int (*ufwiclient_plugin_close_func)(struct ufwiclient_plugin_t *);


/* \cond DOXYGEN_EXCLUDE
 * required to export header without linuxlist.h
 */
#ifndef _LINUX_LLIST_H
struct llist_head {
	struct llist_head *next, *prev;
};
#endif
/* \endcond */

/** \brief Structure for ufwiclient plugin instance
 */
struct ufwiclient_plugin_t {
	struct llist_head list; /**< Doubly-linked list of plugins */

	void *handle; /**< Handle to the dynamic library, returned by dlopen() */
	char *instance_name; /**< Plugin instance name */

	void *plugin_data; /**< Pointer to instance-specific data (can be used by plugin) */

	ufwiclient_plugin_instance_init_func init; /**< Plugin instance init function */
	ufwiclient_plugin_dispatch_func dispatch; /**< Event dispatch function */
	ufwiclient_plugin_close_func close; /**< Plugin close function */
};


/** \brief Signature for plugin init function
 *
 * Argument are:
 *   - api version (to be compared with PLUGIN_API_NUM)
 *   - plugin instance
 * The function should register callbacks into struct ufwiclient_plugin_t
 */
typedef int (*ufwiclient_plugin_init_func)(unsigned int, struct ufwiclient_plugin_t *);
#define NUCLIENT_PLUGIN_INIT		ufwiclient_plugin_init
#define NUCLIENT_PLUGIN_INIT_STR	"ufwiclient_plugin_init"

/** \brief Init plugins infrastructure
 */
int init_plugins(void);

/** \brief Load all plugins (from configuration file)
 */
int load_plugins(void);

/** \brief Dispatch event to all loaded plugins
 */
int plugin_emit_event(plugin_event_t event_id, nuauth_session_t * session, const char *arg);

#endif /* __NUCLIENT_PLUGINS_H__ */

/** @} */

