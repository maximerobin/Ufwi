/*
 ** Copyright (C) 2007-2009 INL
 ** Written by S.Tricaud <stricaud@inl.fr>
 **            L.Defert <ldefert@inl.fr>
 ** INL http://www.inl.fr/
 **
 ** NuSSL: OpenSSL / GnuTLS layer based on libneon
 */


/*
   Standard definitions for neon headers
   Copyright (C) 2003-2006, Joe Orton <joe@manyfish.co.uk>

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

#undef UFWISSL_BEGIN_DECLS
#undef UFWISSL_END_DECLS
#ifdef __cplusplus
# define UFWISSL_BEGIN_DECLS extern "C" {
# define UFWISSL_END_DECLS }
#else
# define UFWISSL_BEGIN_DECLS	/* empty */
# define UFWISSL_END_DECLS	/* empty */
#endif

#ifndef UFWISSL_DEFS_H
#define UFWISSL_DEFS_H

#include <sys/types.h>

#ifdef UFWISSL_LFS
typedef off64_t ufwissl_off_t;
#else
typedef off_t ufwissl_off_t;
#endif

/* define ssize_t for Win32 */
#if defined(WIN32) && !defined(ssize_t)
#define ssize_t int
#endif

#ifdef __GNUC__
#if __GNUC__ >= 3
#define ufwissl_attribute_malloc __attribute__((malloc))
#else
#define ufwissl_attribute_malloc
#endif
#define ufwissl_attribute(x) __attribute__(x)
#else
#define ufwissl_attribute(x)
#define ufwissl_attribute_malloc
#endif

#ifndef UFWISSL_BUFSIZ
#define UFWISSL_BUFSIZ 8192
#endif

#endif				/* UFWISSL_DEFS_H */
