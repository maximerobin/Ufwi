/*
 ** Copyright (C) 2008-2009 INL
 ** Written by Sebastien Tricaud <s.tricaud@inl.fr>
 **            Pierre Chifflier <chifflier@inl.fr>
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
%{
#include <stdio.h>
#include <errno.h>

#include <ufwibase/ufwibase.h>

#define YYDEBUG 0

#define YYERROR_VERBOSE

extern FILE *yyin;
const char *filename;
char *path;

typedef struct config_arg_t {
	struct llist_head* parsed_config;
	char *current_section;
} config_arg_t;
/* Pass the argument to yyparse through to yylex. */
#define YYLEX_PARAM   config_arg
%}

%token TOK_EQUAL
%token	<string> TOK_WORD
%token	<string> TOK_SECTION
%token	<string> TOK_STRING

%union {
	char *string;
	int number;
}

%debug
%destructor { free ($$); } TOK_WORD TOK_SECTION

%locations
%pure_parser

%parse-param { struct config_arg_t* config_arg }

%{

#if YYDEBUG
  static void print_token_value (FILE *, int, YYSTYPE);
# define YYPRINT(file, type, value) print_token_value (file, type, value)
#endif

/* this must come after bison macros, since we need these types to be defined */
int yylex(YYSTYPE* lvalp, YYLTYPE* llocp, struct config_arg_t* config_arg);

void yyerror(YYLTYPE* locp, struct config_arg_t *config_arg, const char* err);


%}

%%
config:		 /* empty */
		| config section
		| config key_value
		;

section:		TOK_SECTION {
				if (config_arg->current_section)
					free(config_arg->current_section);
				config_arg->current_section = $1;
			}
			;
key_value:		TOK_WORD TOK_EQUAL TOK_WORD
			{
				ufwibase_config_table_set_with_section(config_arg->parsed_config, config_arg->current_section, $1, $3);
				free($1);
				free($3);
			}
		|
			TOK_WORD TOK_EQUAL TOK_STRING
			{
				ufwibase_config_table_set_with_section(config_arg->parsed_config, config_arg->current_section, $1, $3);
				free($1);
				free($3);
			}
			;

%%

void yyerror(YYLTYPE* locp, struct config_arg_t *config_arg, const char* err)
{
	fprintf(stderr, "YYERROR:%s\n", err);
}

struct llist_head * parse_configuration(const char *config)
{
	struct llist_head * config_table_list;
	struct config_arg_t config_argument;

	path = str_extract_until(config, '/');
	filename = config;

	yyin = fopen(config, "r");
	if ( ! yyin ) {
		fprintf(stderr, "Cannot open file %s.\n", config);
		return NULL;
	}
	config_table_list = malloc(sizeof(*config_table_list));
	INIT_LLIST_HEAD( config_table_list );

	config_argument.parsed_config = config_table_list;
	config_argument.current_section = NULL;

	yyparse(&config_argument);

	if (config_argument.current_section)
		free(config_argument.current_section);
	return config_table_list;
}

#if YYDEBUG
static void print_token_value (FILE *file, int type, YYSTYPE value)
{
  if (type == TOK_STRING)
    fprintf (file, "s %s", value.string);
  else if (type == TOK_WORD)
    fprintf (file, "w %s", value.string);
  else if (type == TOK_SECTION)
    fprintf (file, "section %s", value.string);
  else if (type == TOK_EQUAL)
    fprintf (file, "= %s", value.string);
  else
    fprintf (file, "unk %s", value.string);
}
#endif



#ifdef _UNIT_TEST_
/* gcc config-parser.lex.c config-parser.yacc.c -o config-parser -D_UNIT_TEST_ -ly -lfl */
int main(void)
{
#if 0
	FILE *fp;

	fp = fopen("../../../conf/nuauth.conf", "r");
	if (!fp) {
		fprintf(stderr, "Cannot open ../../../conf/nuauth.conf");
		return 1;
	}

	parse_configuration(fp, "../../../conf/nuauth.conf");
#endif
	parse_configuration("../../../conf/nuauth.conf");

	return 0;
}
#endif

