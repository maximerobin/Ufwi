/*
 ** Copyright (C) 2007-2009 INL
 ** Written by S.Tricaud <stricaud@inl.fr>
 **            L.Defert <ldefert@inl.fr>
 ** INL http://www.inl.fr/
 **
 ** NuSSL: OpenSSL / GnuTLS layer based on libneon
 */


/*
   Replacement memory allocation handling etc.
   Copyright (C) 1999-2005, Joe Orton <joe@manyfish.co.uk>

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

#ifndef UFWISSL_ALLOC_H
#define UFWISSL_ALLOC_H

#ifdef WIN32
#include <stdlib.h>
#else
#include <sys/types.h>
#endif

#include "ufwissl_defs.h"

UFWISSL_BEGIN_DECLS typedef void (*ufwissl_oom_callback_fn) (void);

/* Set callback which is called if malloc() returns NULL. */
void ufwissl_oom_callback(ufwissl_oom_callback_fn callback);

#ifndef NEON_MEMLEAK
/* Replacements for standard C library memory allocation functions,
 * which never return NULL. If the C library malloc() returns NULL,
 * neon will abort(); calling an OOM callback beforehand if one is
 * registered.  The C library will only ever return NULL if the
 * operating system does not use optimistic memory allocation. */
void *ufwissl_malloc(size_t size) ufwissl_attribute_malloc;
void *ufwissl_calloc(size_t size) ufwissl_attribute_malloc;
void *ufwissl_realloc(void *ptr, size_t s);
char *ufwissl_strdup(const char *s) ufwissl_attribute_malloc;
char *ufwissl_strndup(const char *s, size_t n) ufwissl_attribute_malloc;
#define ufwissl_free free
#endif

UFWISSL_END_DECLS
#endif				/* UFWISSL_ALLOC_H */
