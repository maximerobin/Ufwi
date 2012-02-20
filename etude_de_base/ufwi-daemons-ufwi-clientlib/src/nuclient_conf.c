/*
 ** Copyright(C) 2009 INL
 ** Written by Pierre Chifflier <chifflier@inl.fr>
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

#include <ufwibase.h>

#include "nuclient_conf.h"

#include "config-parser.h"

#include <unistd.h>
#include <stdlib.h>

static struct llist_head *ufwiclient_config_table_list = NULL;

/** \file ufwiclient_conf.c
 * \brief Read configuration file
 */

int ufwiclient_parse_configuration(const char *user_config, const char *global_config)
{
	struct llist_head *new_user_config = NULL, *new_global_config = NULL;

	if (user_config != NULL && access(user_config,R_OK) == 0) {
		new_user_config = parse_configuration(user_config);
	}

	if (access(global_config,R_OK) == 0) {
		new_global_config = parse_configuration(global_config);
	}

	if (ufwiclient_config_table_list != NULL)
		ufwiclient_config_table_destroy();

	if (new_user_config != NULL) {
		if (new_global_config == NULL) {
			/* user, but no global config */
			ufwiclient_config_table_list = new_user_config;
			return 0;
		}
		/* we have both config files, merge configs (user values
		 * override global values).
		 * Note: this is a O(n^2) operation, don't abuse it !
		 */
		 {
			 struct config_table_t *entry;

			llist_for_each_entry(entry, new_user_config, list) {
				ufwibase_config_table_set(new_global_config, entry->key, entry->value);
			}
			ufwibase_config_table_destroy(new_user_config);
			ufwiclient_config_table_list = new_global_config;
			return 0;
		 }
	} else {
		if (new_global_config != NULL) {
			/* global, but no user config */
			ufwiclient_config_table_list = new_global_config;
			return 0;
		}
		/* no global or user config, defaults to empty */
		ufwiclient_config_table_list = malloc(sizeof(struct llist_head));
		INIT_LLIST_HEAD( ufwiclient_config_table_list );
	}

	return 0;
}



char *ufwiclient_config_table_get(const char *key)
{
	return ufwibase_config_table_get(ufwiclient_config_table_list, key);
}

char *ufwiclient_config_table_get_alwaysstring(char *key)
{
	return ufwibase_config_table_get_alwaysstring(ufwiclient_config_table_list, key);
}

char *ufwiclient_config_table_get_or_default(char *key, char *replace)
{
	return ufwibase_config_table_get_or_default(ufwiclient_config_table_list, key, replace);
}

int ufwiclient_config_table_get_or_default_int(char *key, int defint)
{
	return ufwibase_config_table_get_or_default_int(ufwiclient_config_table_list, key, defint);
}

void ufwiclient_config_table_destroy(void)
{
	return ufwibase_config_table_destroy(ufwiclient_config_table_list);
	ufwiclient_config_table_list = NULL;
}

void ufwiclient_config_table_print(void *userdata, void (*func)(void *data, char *keyeqval))

{
	return ufwibase_config_table_print(ufwiclient_config_table_list,userdata,func);
}

void ufwiclient_config_table_walk(void *userdata, void (*func)(void *data, char *key, char *val))

{
	struct config_table_t *config_table;

	llist_for_each_entry(config_table, ufwiclient_config_table_list, list) {
		func(userdata, config_table->key, config_table->value);
	}
}

