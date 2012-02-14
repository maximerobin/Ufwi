/*
 ** Copyright (C) 2007-2009 INL
 ** Written by S.Tricaud <stricaud@inl.fr>
 **            L.Defert <ldefert@inl.fr>
 ** INL http://www.inl.fr/
 **
 ** NuSSL: OpenSSL / GnuTLS layer based on libneon
 */


/*
   String utility functions
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

#ifndef UFWISSL_STRING_H
#define UFWISSL_STRING_H

#include "ufwissl_defs.h"
#include "ufwissl_alloc.h"

#include <stdio.h>
#include <stdarg.h>

UFWISSL_BEGIN_DECLS
/* ufwissl_token and ufwissl_qtoken return the next token in *str before either
 * the next separator character 'sep' or the NUL terminator.
 * ufwissl_qtoken skips over any parts quoted using a pair of any one of
 * the characters given in 'quotes'.  After returning, *str will point
 * to the next character after the separator, or NULL if no separator
 * character was found.
 *
 * ufwissl_qtoken will return NULL if unterminated quotes are found. */
char *ufwissl_token(char **str, char sep);
char *ufwissl_qtoken(char **str, char sep, const char *quotes);

/* Return portion of 'str' with any characters in 'whitespace' shaved
 * off the beginning and end.  Modifies str in-place. */
char *ufwissl_shave(char *str, const char *whitespace);

/* Cleanse 'str' of non-printable (e.g. control) characters.  'str' is
 * modified in-place, and returned. */
char *ufwissl_strclean(char *str);

/* Encode 'len' bytes of 'text' to base64.  Returns malloc-allocated
 * NUL-terminated buffer which the caller must free(). */
char *ufwissl_base64(const unsigned char *text, size_t len);

/* Decode NUL-terminated base64-encoded string 'data', placing
 * malloc-allocated raw decoder output in '*out'.  Returns length, or
 * zero on decode error (in which case the content of *out is
 * undefined). */
size_t ufwissl_unbase64(const char *data, unsigned char **out);

/* Dynamically-allocated string buffer.  A string buffer which grows
 * dynamically . (Strings are zero-terminated still).  A
 * string buffer ufwissl_buffer which grows dynamically with the string. */
typedef struct {
	char *data;		/* contents: NUL-terminated string */
	size_t used;		/* strlen(data) + 1 */
	size_t length;		/* number of bytes allocated */
} ufwissl_buffer;

/* Create a new string buffer object. */
ufwissl_buffer *ufwissl_buffer_create(void);

/* Create a new string buffer object with at least 'size' bytes of
 * allocated space. */
ufwissl_buffer *ufwissl_buffer_ncreate(size_t size);

/* Returns size of data in buffer, equiv to strlen(ufwissl_buffer_data(buf)) */
#define ufwissl_buffer_size(buf) ((buf)->used - 1)

/* Concatenate all given strings onto the end of the buffer.  The
 * strings must all be NUL-terminated, and MUST be followed by a NULL
 * argument marking the end of the list.  */
void ufwissl_buffer_concat(ufwissl_buffer * buf, ...);

/* Append a NUL-terminated string 'str' to buf. */
void ufwissl_buffer_zappend(ufwissl_buffer * buf, const char *str);

/* Append 'len' bytes of 'data' to buf, where 'data' does not contain
 * a NUL terminator.  (A NUL terminator is appended to buf) */
void ufwissl_buffer_append(ufwissl_buffer * buf, const char *data, size_t len);

/* Print a string to the end of the buffer using printf-style format
 * string 'format' and subsqeuent arguments.  At most 'max' characters
 * are appended; the number of characters appended (excluding the NUL
 * terminator) is returned.  Behaviour is undefined if 'max' is passed
 * as zero. */
size_t ufwissl_buffer_snprintf(ufwissl_buffer * buf, size_t max,
			     const char *format, ...)
ufwissl_attribute((format(printf, 3, 4)));

/* Append a literal, NUL-terminated constant string 'str' to buffer
 * 'buf'. */
#define ufwissl_buffer_czappend(buf, str) \
ufwissl_buffer_append((buf), (str), sizeof((str)) - 1)

/* Clear the string buffer 'buf', making it equivalent to the empty
 * string. */
void ufwissl_buffer_clear(ufwissl_buffer * buf);

/* Grow the allocated size of string buffer 'buf' to at least 'size'
 * bytes. */
void ufwissl_buffer_grow(ufwissl_buffer * buf, size_t size);

/* Re-establish the 'used' invariant if the string buffer data field is
 * altered directly. */
void ufwissl_buffer_altered(ufwissl_buffer * buf);

/* Destroy the string buffer object 'buf' without deallocating the
 * data string.  The data string must subsequently be freed using
 * ufwissl_free(). */
char *ufwissl_buffer_finish(ufwissl_buffer * buf);

/* Destroy a string buffer object. */
void ufwissl_buffer_destroy(ufwissl_buffer * buf);

/* Thread-safe strerror() wrapper; place system error for errno value
 * 'errnum' in 'buffer', which is of length 'buflen'.  Returns
 * 'buffer'. */
char *ufwissl_strerror(int errnum, char *buffer, size_t buflen);

/* ufwissl_strnzcpy copies at most 'n'-1 bytes of 'src' to 'dest', and
 * ensures that 'dest' is subsequently NUL-terminated. */
#define ufwissl_strnzcpy(dest, src, n) do { size_t ufwissl__nm1 = (n) - 1;      \
strncpy(dest, src, ufwissl__nm1); dest[ufwissl__nm1] = '\0'; } while (0)

/* Return malloc-allocated concatenation of all NUL-terminated string
 * arguments, up to a terminating NULL pointer. */
char *ufwissl_concat(const char *str, ...);

/* Wrapper for snprintf: always NUL-terminates returned buffer, and
 * returns strlen(str). */
size_t ufwissl_snprintf(char *str, size_t size, const char *fmt, ...)
ufwissl_attribute((format(printf, 3, 4)));

/* Wrapper for vsnprintf. */
size_t ufwissl_vsnprintf(char *str, size_t size, const char *fmt, va_list ap)
ufwissl_attribute((format(printf, 3, 0)));

/* Implementations of strcasecmp and strncasecmp which behave as
 * defined by the ANSI C strcasecmp() and strncasecmp() when in the
 * POSIX locale; i.e. ignoring the process locale. */

/* Compares 's1' and 's2', ignoring differences in case. */
int ufwissl_strcasecmp(const char *s1, const char *s2);
/* Compares up to 'n' characters of 's1' and 's2', ignoring
 * differences in case. */
int ufwissl_strncasecmp(const char *s1, const char *s2, size_t n);

/* Return lowercase 'c' as in POSIX locale; note difference from ANSI
 * C semantics as both the argument and return value are unsigned
 * char. */
#define ufwissl_tolower(c) (ufwissl_tolower_array()[(unsigned char)c])

const unsigned char *ufwissl_tolower_array(void);

/* Convert an ASCII hexadecimal character in the ranges '0'..'9'
 * 'a'..'f' 'A'..'F' to its numeric equivalent. */
#define UFWISSL_ASC2HEX(x) (((x) <= '9') ? ((x) - '0') : \
                       (ufwissl_tolower((x)) + 10 - 'a'))

/* Convert an integer in the range 0..15 to the equivalent (lowercase)
 * ASCII hexadecimal equivalent character, in the range '0..9,'a..f' */
#define UFWISSL_HEX2ASC(x) ((char) ((x) > 9 ? ((x) - 10 + 'a') : ((x) + '0')))

UFWISSL_END_DECLS
#endif				/* UFWISSL_STRING_H */
