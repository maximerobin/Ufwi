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
   strcasecmp/strncasecmp implementations are:
   Copyright (C) 1991, 1992, 1995, 1996, 1997 Free Software Foundation, Inc.
   This file is part of the GNU C Library.

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

/* Enable C99 features like vsnprintf() */
/* #define _ISOC99_SOURCE */

#include <config.h>
#include "ufwissl_config.h"

#include <stdlib.h>
#include <string.h>
#ifdef HAVE_UNISTD_H
# include <unistd.h>
#endif
#include <stdio.h>

#include <ctype.h>		/* for isprint() etc in ufwissl_strclean() */

#include "ufwissl_alloc.h"
#include "ufwissl_string.h"

char *ufwissl_token(char **str, char separator)
{
	char *ret = *str, *pnt = strchr(*str, separator);

	if (pnt) {
		*pnt = '\0';
		*str = pnt + 1;
	} else {
		/* no separator found: return end of string. */
		*str = NULL;
	}

	return ret;
}

char *ufwissl_qtoken(char **str, char separator, const char *quotes)
{
	char *pnt, *ret = NULL;

	for (pnt = *str; *pnt != '\0'; pnt++) {
		char *quot = strchr(quotes, *pnt);

		if (quot) {
			char *qclose = strchr(pnt + 1, *quot);

			if (!qclose) {
				/* no closing quote: invalid string. */
				return NULL;
			}

			pnt = qclose;
		} else if (*pnt == separator) {
			/* found end of token. */
			*pnt = '\0';
			ret = *str;
			*str = pnt + 1;
			return ret;
		}
	}

	/* no separator found: return end of string. */
	ret = *str;
	*str = NULL;
	return ret;
}

char *ufwissl_shave(char *str, const char *whitespace)
{
	char *pnt, *ret = str;

	while (*ret != '\0' && strchr(whitespace, *ret) != NULL) {
		ret++;
	}

	/* pnt points at the NUL terminator. */
	pnt = &ret[strlen(ret)];

	while (pnt > ret && strchr(whitespace, *(pnt - 1)) != NULL) {
		pnt--;
	}

	*pnt = '\0';
	return ret;
}

void ufwissl_buffer_clear(ufwissl_buffer * buf)
{
	memset(buf->data, 0, buf->length);
	buf->used = 1;
}

/* Grows for given size, returns 0 on success, -1 on error. */
void ufwissl_buffer_grow(ufwissl_buffer * buf, size_t newsize)
{
#define UFWISSL_BUFFER_GROWTH 512
	if (newsize > buf->length) {
		/* If it's not big enough already... */
		buf->length =
		    ((newsize / UFWISSL_BUFFER_GROWTH) +
		     1) * UFWISSL_BUFFER_GROWTH;

		/* Reallocate bigger buffer */
		buf->data = ufwissl_realloc(buf->data, buf->length);
	}
}

static size_t count_concat(va_list * ap)
{
	size_t total = 0;
	char *next;

	while ((next = va_arg(*ap, char *)) != NULL)
		 total += strlen(next);

	return total;
}

static void do_concat(char *str, va_list * ap)
{
	char *next;

	while ((next = va_arg(*ap, char *)) != NULL) {
#ifdef HAVE_STPCPY
		str = stpcpy(str, next);
#else
		size_t len = strlen(next);
		memcpy(str, next, len);
		str += len;
#endif
	}
}

void ufwissl_buffer_concat(ufwissl_buffer * buf, ...)
{
	va_list ap;
	ssize_t total;

	va_start(ap, buf);
	total = buf->used + count_concat(&ap);
	va_end(ap);

	/* Grow the buffer */
	ufwissl_buffer_grow(buf, total);

	va_start(ap, buf);
	do_concat(buf->data + buf->used - 1, &ap);
	va_end(ap);

	buf->used = total;
	buf->data[total - 1] = '\0';
}

char *ufwissl_concat(const char *str, ...)
{
	va_list ap;
	size_t total, slen = strlen(str);
	char *ret;

	va_start(ap, str);
	total = slen + count_concat(&ap);
	va_end(ap);

	ret = memcpy(ufwissl_malloc(total + 1), str, slen);

	va_start(ap, str);
	do_concat(ret + slen, &ap);
	va_end(ap);

	ret[total] = '\0';
	return ret;
}

/* Append zero-terminated string... returns 0 on success or -1 on
 * realloc failure. */
void ufwissl_buffer_zappend(ufwissl_buffer * buf, const char *str)
{
	ufwissl_buffer_append(buf, str, strlen(str));
}

void ufwissl_buffer_append(ufwissl_buffer * buf, const char *data, size_t len)
{
	ufwissl_buffer_grow(buf, buf->used + len);
	memcpy(buf->data + buf->used - 1, data, len);
	buf->used += len;
	buf->data[buf->used - 1] = '\0';
}

size_t ufwissl_buffer_snprintf(ufwissl_buffer * buf, size_t max,
			     const char *fmt, ...)
{
	va_list ap;
	size_t ret;

	ufwissl_buffer_grow(buf, buf->used + max);

	va_start(ap, fmt);
	ret = ufwissl_vsnprintf(buf->data + buf->used - 1, max, fmt, ap);
	va_end(ap);
	buf->used += ret;

	return ret;
}

ufwissl_buffer *ufwissl_buffer_create(void)
{
	return ufwissl_buffer_ncreate(512);
}

ufwissl_buffer *ufwissl_buffer_ncreate(size_t s)
{
	ufwissl_buffer *buf = ufwissl_malloc(sizeof(*buf));
	buf->data = ufwissl_malloc(s);
	buf->data[0] = '\0';
	buf->length = s;
	buf->used = 1;
	return buf;
}

void ufwissl_buffer_destroy(ufwissl_buffer * buf)
{
	ufwissl_free(buf->data);
	ufwissl_free(buf);
}

char *ufwissl_buffer_finish(ufwissl_buffer * buf)
{
	char *ret = buf->data;
	ufwissl_free(buf);
	return ret;
}

void ufwissl_buffer_altered(ufwissl_buffer * buf)
{
	buf->used = strlen(buf->data) + 1;
}

static const char b64_alphabet[] =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz" "0123456789+/=";

char *ufwissl_base64(const unsigned char *text, size_t inlen)
{
	/* The tricky thing about this is doing the padding at the end,
	 * doing the bit manipulation requires a bit of concentration only */
	char *buffer, *point;
	size_t outlen;

	/* Use 'buffer' to store the output. Work out how big it should be...
	 * This must be a multiple of 4 bytes */

	outlen = (inlen * 4) / 3;
	if ((inlen % 3) > 0)	/* got to pad */
		outlen += 4 - (inlen % 3);

	buffer = ufwissl_malloc(outlen + 1);	/* +1 for the \0 */

	/* now do the main stage of conversion, 3 bytes at a time,
	 * leave the trailing bytes (if there are any) for later */

	for (point = buffer; inlen >= 3; inlen -= 3, text += 3) {
		*(point++) = b64_alphabet[(*text) >> 2];
		*(point++) =
		    b64_alphabet[((*text) << 4 & 0x30) | (*(text + 1)) >>
				 4];
		*(point++) =
		    b64_alphabet[((*(text + 1)) << 2 & 0x3c) |
				 (*(text + 2)) >> 6];
		*(point++) = b64_alphabet[(*(text + 2)) & 0x3f];
	}

	/* Now deal with the trailing bytes */
	if (inlen > 0) {
		/* We always have one trailing byte */
		*(point++) = b64_alphabet[(*text) >> 2];
		*(point++) = b64_alphabet[(((*text) << 4 & 0x30) |
					   (inlen ==
					    2 ? (*(text + 1)) >> 4 : 0))];
		*(point++) =
		    (inlen ==
		     1 ? '=' : b64_alphabet[(*(text + 1)) << 2 & 0x3c]);
		*(point++) = '=';
	}

	/* Null-terminate */
	*point = '\0';

	return buffer;
}

/* VALID_B64: fail if 'ch' is not a valid base64 character */
#define VALID_B64(ch) (((ch) >= 'A' && (ch) <= 'Z') || \
                       ((ch) >= 'a' && (ch) <= 'z') || \
                       ((ch) >= '0' && (ch) <= '9') || \
                       (ch) == '/' || (ch) == '+' || (ch) == '=')

/* DECODE_B64: decodes a valid base64 character. */
#define DECODE_B64(ch) ((ch) >= 'a' ? ((ch) + 26 - 'a') : \
                        ((ch) >= 'A' ? ((ch) - 'A') : \
                         ((ch) >= '0' ? ((ch) + 52 - '0') : \
                          ((ch) == '+' ? 62 : 63))))

size_t ufwissl_unbase64(const char *data, unsigned char **out)
{
	size_t inlen = strlen(data);
	unsigned char *outp;
	const unsigned char *in;

	if (inlen == 0 || (inlen % 4) != 0)
		return 0;

	outp = *out = ufwissl_malloc(inlen * 3 / 4);

	for (in = (const unsigned char *) data; *in; in += 4) {
		unsigned int tmp;
		if (!VALID_B64(in[0]) || !VALID_B64(in[1])
		    || !VALID_B64(in[2]) || !VALID_B64(in[3])
		    || in[0] == '=' || in[1] == '=' || (in[2] == '='
							&& in[3] != '=')) {
			ufwissl_free(*out);
			return 0;
		}
		tmp = (DECODE_B64(in[0]) & 0x3f) << 18 |
		    (DECODE_B64(in[1]) & 0x3f) << 12;
		*outp++ = (tmp >> 16) & 0xff;
		if (in[2] != '=') {
			tmp |= (DECODE_B64(in[2]) & 0x3f) << 6;
			*outp++ = (tmp >> 8) & 0xff;
			if (in[3] != '=') {
				tmp |= DECODE_B64(in[3]) & 0x3f;
				*outp++ = tmp & 0xff;
			}
		}
	}

	return outp - *out;
}

char *ufwissl_strclean(char *str)
{
	char *pnt;
	for (pnt = str; *pnt; pnt++)
		if (iscntrl(*pnt) || !isprint(*pnt))
			*pnt = ' ';
	return str;
}

char *ufwissl_strerror(int errnum, char *buf, size_t buflen)
{
#ifdef HAVE_STRERROR_R
#ifdef STRERROR_R_CHAR_P
	/* glibc-style strerror_r which may-or-may-not use provided buffer. */
	char *ret = strerror_r(errnum, buf, buflen);
	if (ret != buf)
		ufwissl_strnzcpy(buf, ret, buflen);
#else				/* POSIX-style strerror_r: */
	char tmp[256];

	if (strerror_r(errnum, tmp, sizeof tmp) == 0)
		ufwissl_strnzcpy(buf, tmp, buflen);
	else
		ufwissl_snprintf(buf, buflen, "Unknown error %d", errnum);
#endif
#else				/* no strerror_r: */
	ufwissl_strnzcpy(buf, strerror(errnum), buflen);
#endif
	return buf;
}


/* Wrapper for ufwissl_snprintf. */
size_t ufwissl_snprintf(char *str, size_t size, const char *fmt, ...)
{
	va_list ap;
	va_start(ap, fmt);
#ifdef HAVE_TRIO
	trio_vsnprintf(str, size, fmt, ap);
#else
	vsnprintf(str, size, fmt, ap);
#endif
	va_end(ap);
	str[size - 1] = '\0';
	return strlen(str);
}

/* Wrapper for ufwissl_vsnprintf. */
size_t ufwissl_vsnprintf(char *str, size_t size, const char *fmt, va_list ap)
{
#ifdef HAVE_TRIO
	trio_vsnprintf(str, size, fmt, ap);
#else
	vsnprintf(str, size, fmt, ap);
#endif
	str[size - 1] = '\0';
	return strlen(str);
}

/* Locale-independent strcasecmp implementations. */
static const unsigned char ascii_tolower[256] = {
	0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
	0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f,
	0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17,
	0x18, 0x19, 0x1a, 0x1b, 0x1c, 0x1d, 0x1e, 0x1f,
	0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27,
	0x28, 0x29, 0x2a, 0x2b, 0x2c, 0x2d, 0x2e, 0x2f,
	0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37,
	0x38, 0x39, 0x3a, 0x3b, 0x3c, 0x3d, 0x3e, 0x3f,
	0x40, 0x61, 0x62, 0x63, 0x64, 0x65, 0x66, 0x67,
	0x68, 0x69, 0x6a, 0x6b, 0x6c, 0x6d, 0x6e, 0x6f,
	0x70, 0x71, 0x72, 0x73, 0x74, 0x75, 0x76, 0x77,
	0x78, 0x79, 0x7a, 0x5b, 0x5c, 0x5d, 0x5e, 0x5f,
	0x60, 0x61, 0x62, 0x63, 0x64, 0x65, 0x66, 0x67,
	0x68, 0x69, 0x6a, 0x6b, 0x6c, 0x6d, 0x6e, 0x6f,
	0x70, 0x71, 0x72, 0x73, 0x74, 0x75, 0x76, 0x77,
	0x78, 0x79, 0x7a, 0x7b, 0x7c, 0x7d, 0x7e, 0x7f,
	0x80, 0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87,
	0x88, 0x89, 0x8a, 0x8b, 0x8c, 0x8d, 0x8e, 0x8f,
	0x90, 0x91, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97,
	0x98, 0x99, 0x9a, 0x9b, 0x9c, 0x9d, 0x9e, 0x9f,
	0xa0, 0xa1, 0xa2, 0xa3, 0xa4, 0xa5, 0xa6, 0xa7,
	0xa8, 0xa9, 0xaa, 0xab, 0xac, 0xad, 0xae, 0xaf,
	0xb0, 0xb1, 0xb2, 0xb3, 0xb4, 0xb5, 0xb6, 0xb7,
	0xb8, 0xb9, 0xba, 0xbb, 0xbc, 0xbd, 0xbe, 0xbf,
	0xc0, 0xc1, 0xc2, 0xc3, 0xc4, 0xc5, 0xc6, 0xc7,
	0xc8, 0xc9, 0xca, 0xcb, 0xcc, 0xcd, 0xce, 0xcf,
	0xd0, 0xd1, 0xd2, 0xd3, 0xd4, 0xd5, 0xd6, 0xd7,
	0xd8, 0xd9, 0xda, 0xdb, 0xdc, 0xdd, 0xde, 0xdf,
	0xe0, 0xe1, 0xe2, 0xe3, 0xe4, 0xe5, 0xe6, 0xe7,
	0xe8, 0xe9, 0xea, 0xeb, 0xec, 0xed, 0xee, 0xef,
	0xf0, 0xf1, 0xf2, 0xf3, 0xf4, 0xf5, 0xf6, 0xf7,
	0xf8, 0xf9, 0xfa, 0xfb, 0xfc, 0xfd, 0xfe, 0xff
};

#define TOLOWER(ch) ascii_tolower[ch]

const unsigned char *ufwissl_tolower_array(void)
{
	return ascii_tolower;
}

int ufwissl_strcasecmp(const char *s1, const char *s2)
{
	const unsigned char *p1 = (const unsigned char *) s1;
	const unsigned char *p2 = (const unsigned char *) s2;
	unsigned char c1, c2;

	if (p1 == p2)
		return 0;

	do {
		c1 = TOLOWER(*p1++);
		c2 = TOLOWER(*p2++);
		if (c1 == '\0')
			break;
	} while (c1 == c2);

	return c1 - c2;
}

int ufwissl_strncasecmp(const char *s1, const char *s2, size_t n)
{
	const unsigned char *p1 = (const unsigned char *) s1;
	const unsigned char *p2 = (const unsigned char *) s2;
	unsigned char c1, c2;

	if (p1 == p2 || n == 0)
		return 0;

	do {
		c1 = TOLOWER(*p1++);
		c2 = TOLOWER(*p2++);
		if (c1 == '\0' || c1 != c2)
			return c1 - c2;
	} while (--n > 0);

	return c1 - c2;
}
