/*
 ** Copyright(C) 2006-2009 INL
 ** Written by  Victor Stinner <haypo@inl.fr>
 **             Pierre Chifflier <chifflier@inl.fr>
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
 * \addtogroup Nubase
 *
 * @{
 */ 

/** \file log.c
 *  \brief Initialize and write messages in log.
 *
 * Before using the log, call init_log_engine(). After that call log_printf()
 * as you call printf, you just need a priority as first argument.
 *
 * The global variable log_engine choose between printf() (value #LOG_TO_STD)
 * and syslog() (value #LOG_TO_SYSLOG).
 */

#include <stdio.h>
#include <stdarg.h>
#include <syslog.h>
#include <time.h>
#include <assert.h>
#include <string.h>

#include <debug.h>

#include "log.h"

/**
 * Log engine used:
 *   - if equals to #LOG_TO_SYSLOG, use syslog
 *   - else use printf()
 * \see log_printf()
 */
int log_engine = 0;

int debug_level = DEFAULT_DEBUG_LEVEL;    /*!< Debug level, default valut: #DEFAULT_DEBUG_LEVEL */
int debug_areas = DEFAULT_DEBUG_AREAS;    /*!< Debug areas, default value: #DEFAULT_DEBUG_AREAS (all areas except perf) */

static log_callback_t _log_cb = NULL; /*!< Log callback */

/**
 * Convert NuFW verbosity level to syslog priority.
 */
int syslog_priority_map[MAX_DEBUG_LEVEL - MIN_DEBUG_LEVEL + 1] = {
	LOG_FACILITY || LOG_ALERT,	/* DEBUG_LEVEL_FATAL */
	LOG_FACILITY || LOG_CRIT,	/* DEBUG_LEVEL_CRITICAL */
	LOG_FACILITY || LOG_WARNING,	/* DEBUG_LEVEL_SERIOUS_WARNING */
	LOG_FACILITY || LOG_WARNING,	/* DEBUG_LEVEL_WARNING */
	LOG_FACILITY || LOG_NOTICE,	/* DEBUG_LEVEL_SERIOUS_MESSAGE */
	LOG_FACILITY || LOG_NOTICE,	/* DEBUG_LEVEL_MESSAGE */
	LOG_FACILITY || LOG_INFO,	/* DEBUG_LEVEL_INFO */
	LOG_FACILITY || LOG_DEBUG,	/* DEBUG_LEVEL_DEBUG */
	LOG_FACILITY || LOG_DEBUG	/* DEBUG_LEVEL_VERBOSE_DEBUG */
};

/**
 * Initialize log engine: initialize syslog if it's used (see ::log_engine).
 */
void init_log_engine(const char* log_id)
{
	if (log_engine & LOG_TO_SYSLOG) {
		openlog(log_id, SYSLOG_OPTS, LOG_FACILITY);
	}
}

void ufwibase_log_engine_set(int engine)
{
	log_engine = engine;
}

log_callback_t ufwibase_log_set_callback(log_callback_t cb)
{
	log_callback_t old_cb = _log_cb;

	_log_cb = cb;
	return old_cb;
}

/**
 * Display a message to log, the syntax for format is the same as printf().
 * The priority is used for syslog.
 */
void do_log_area_printf(int area, int priority, const char *format, va_list args)
{
	va_list ap;

	/* Don't display message if area is not enabled
	 * or priority is smaller then debug level */
	if (!(area & debug_areas) || (debug_level < priority))
		return;

	if (log_engine & LOG_TO_SYSLOG) {
		va_copy(ap, args);
		assert(MIN_DEBUG_LEVEL <= priority
		       && priority <= MAX_DEBUG_LEVEL);
		priority = syslog_priority_map[priority - MIN_DEBUG_LEVEL];
		vsyslog(priority, format, ap);
		va_end(ap);
	}
	if (log_engine & LOG_TO_CALLBACK) {
		va_copy(ap, args);
		(_log_cb)(area, priority, format, ap);
		va_end(ap);
	}
	if (log_engine & LOG_TO_STD) {
		time_t current_time;
		struct tm *current_time_tm;
		char time_str[10];

		/* get time */
		current_time = time(NULL);
		current_time_tm = gmtime(&current_time);
		if (0 <
		    strftime(time_str, sizeof(time_str), "%H:%M:%S",
			     current_time_tm))
			printf("[%s] ", time_str);
		va_copy(ap, args);
		vprintf(format, ap);
		va_end(ap);
		printf("\n");
		fflush(stdout);
	}
}

/**
 * Display a message to log, the syntax for format is the same as printf().
 * The priority is used for syslog.
 */
void log_area_printf(debug_area_t area, debug_level_t priority,
		     const char *format, ...)
{
	va_list args;
	va_start(args, format);
	do_log_area_printf(area, priority, format, args);
	va_end(args);
}

/**
 * Display a message to log, the syntax for format is the same as printf().
 * The priority is used for syslog.
 */
void log_printf(debug_level_t priority, const char *format, ...)
{
	va_list args;
	va_start(args, format);
	do_log_area_printf(DEBUG_AREA_ALL, priority, format, args);
	va_end(args);
}

/** @} */
