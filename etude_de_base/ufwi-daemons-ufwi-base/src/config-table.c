/*
 ** Copyright(C) 2008-2009 INL
 ** Written by Sebastien Tricaud <s.tricaud@inl.fr>
 **            Pierre Chifflier <chifflier@inl.fr>
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

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <errno.h>

#include <ufwibase.h>

#include "linuxlist.h"
#include "config-table.h"

/**
 * \addtogroup Nubase
 *
 * @{
 */

/**
 * \file config-table.c
 * \brief Configuration file parsing function
 */

char *ufwibase_config_table_get(struct llist_head *config_table_list, const char *key)
{
	struct config_table_t *config_table;

	struct llist_head *pos;
	llist_for_each(pos, config_table_list) {
		config_table = llist_entry(pos, struct config_table_t, list);
		if (!strcmp(config_table->key, key)) {
			return config_table->value;
		}
	}

	return NULL;
}

char *ufwibase_config_table_get_alwaysstring(struct llist_head *config_table_list, char *key)
{
	char *str;

	str = ufwibase_config_table_get(config_table_list, key);
	if ( ! str ) return "";

	return str;
}

char *ufwibase_config_table_get_or_default(struct llist_head *config_table_list, char *key, char *replace)
{
	char *str;

	str = ufwibase_config_table_get(config_table_list, key);

	if (str) {
		return strdup(str);
	} else if (replace) {
		return strdup(replace);
	} else {
		return strdup("");
	}

}

struct config_table_t *ufwibase_config_table_append(struct llist_head *config_table_list, char *key, char *value)
{
	struct config_table_t *config_table;

	if (ufwibase_config_table_get(config_table_list, key))
		return NULL;

	config_table = malloc(sizeof(*config_table));
	if ( ! config_table ) {
		errno = ENOMEM;
		return NULL;
	}

	config_table->key = strdup(key);
	config_table->value = strdup(value);

	llist_add_tail(&config_table->list, config_table_list);


	return config_table;
}

struct config_table_t *ufwibase_config_table_append_with_section(struct llist_head *config_table_list, char *section, char *key, char *value)
{
	char buffer[4096];
	int ret;

	if (section == NULL || strcasecmp(section,"global")==0) {
		return ufwibase_config_table_append(config_table_list, key, value);
	}

	ret = snprintf(buffer, sizeof(buffer), "%s/%s", section, key);
	if (ret >= (int)sizeof(buffer))
		return NULL;

	return ufwibase_config_table_append(config_table_list, buffer, value);
}

struct config_table_t *ufwibase_config_table_set_with_section(struct llist_head *config_table_list, char *section, char *key, char *value)
{
	char buffer[4096];
	int ret;

	if (section == NULL || strcasecmp(section,"global")==0) {
		return ufwibase_config_table_set(config_table_list, key, value);
	}

	ret = snprintf(buffer, sizeof(buffer), "%s/%s", section, key);
	if (ret >= (int)sizeof(buffer))
		return NULL;

	return ufwibase_config_table_set(config_table_list, buffer, value);
}

void ufwibase_config_table_destroy(struct llist_head *config_table_list)
{
	struct config_table_t *config_table;

	while(!llist_empty(config_table_list)) {
		config_table = llist_entry(config_table_list->next, struct config_table_t, list);
		llist_del(&config_table->list);
		free(config_table->key);
		free(config_table->value);
		free(config_table);
	}

	// Reinitialize the list for reuse
	INIT_LLIST_HEAD(config_table_list);
}

/* Similar to ufwibase_config_table_append,
 * but does not check for existing value
 * and if it exists, free() it */
struct config_table_t *ufwibase_config_table_set(struct llist_head *config_table_list, char *key, char *value)
{
	struct config_table_t *config_table;

	/* It does not exists so we use _append*/
	if ( ! ufwibase_config_table_get(config_table_list, key) ) {
		return ufwibase_config_table_append(config_table_list, key, value);
	}

	{
		struct llist_head *pos;
		llist_for_each(pos, config_table_list) {
			config_table = llist_entry(pos, struct config_table_t, list);
			if (!strncmp(key, config_table->key, strlen(config_table->key))) {
				llist_del(&config_table->list);
				return ufwibase_config_table_append(config_table_list, key, value);
			}
		}
	}

	return NULL;
}

int ufwibase_config_table_get_or_default_int(struct llist_head *config_table_list, char *key, int defint)
{
	char *str;
	int i;

	str = ufwibase_config_table_get_or_default(config_table_list, key, str_itoa(defint));

	i = atoi(str);

	return i;
}

void ufwibase_config_table_print(struct llist_head *config_table_list, void *userdata, void (*func)(void *data, char *keyeqval))
{
	struct config_table_t *config_table;
	char *buffer;
	size_t buffer_len;

	struct llist_head *pos;
	llist_for_each(pos, config_table_list) {
		config_table = llist_entry(pos, struct config_table_t, list);
		buffer_len = strlen((const char *)config_table->key) + 1 + strlen((const char *)config_table->value) + 1;
		buffer = malloc(buffer_len);
		secure_snprintf(buffer,  buffer_len,
				"%s=%s",(char *)config_table->key, (char *)config_table->value); 
		
		func(userdata, buffer);

		free(buffer);
	}
}

#ifdef _UNIT_TEST_
#include <stdio.h>
int main(void)
{
	struct config_table_t *config_table;
	int i = 0;

	ufwibase_config_table_append("foo", "bar");
	ufwibase_config_table_append("foo", "bar");
	ufwibase_config_table_append("nu", "pik");
	ufwibase_config_table_append("tout", "foulcan");
	ufwibase_config_table_append("jean", "nemard");

	printf("\n........................\nllist_for_each_entry\n........................\n");

	llist_for_each_entry(config_table, &config_table_list, list) {
		printf("key=%s, value=%s\n", config_table->key, config_table->value);
	}

	printf("\n........................\nufwibase_config_table_get\n........................\n");
	printf("The value for 'nu' is '%s'\n", ufwibase_config_table_get("nu"));

}
#endif

/** @} */
