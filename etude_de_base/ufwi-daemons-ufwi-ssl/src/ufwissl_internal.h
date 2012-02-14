/*
 ** Copyright (C) 2007-2009 INL
 ** Written by S.Tricaud <stricaud@inl.fr>
 **            L.Defert <ldefert@inl.fr>
 ** INL http://www.inl.fr/
 **
 ** NuSSL: OpenSSL / GnuTLS layer based on libneon

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


/*
   Global interfaces private to neon.
   Copyright (C) 2005-2006, Joe Orton <joe@manyfish.co.uk>

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

*/

/* NOTE WELL: The interfaces defined in this file are internal to neon
 * and MUST NOT be used by neon-based applications. */

#ifndef UFWISSL_INTERNAL_H
#define UFWISSL_INTERNAL_H 1

#include "ufwissl_config.h"

#ifdef HAVE_SYS_LIMITS_H
#include <sys/limits.h>
#endif
#ifdef HAVE_LIMITS_H
#include <limits.h>		/* for UINT_MAX etc */
#endif

#include "ufwissl_defs.h"

#undef _
#ifdef UFWISSL_HAVE_I18N
#include <libintl.h>
#define _(str) dgettext(PACKAGE_NAME, str)
#else
#define _(str) (str)
#endif				/* UFWISSL_ENABLE_NLS */
#define N_(str) (str)

#if !defined(LONG_LONG_MAX) && defined(LLONG_MAX)
#define LONG_LONG_MAX LLONG_MAX
#elif !defined(LONG_LONG_MAX) && defined(LONGLONG_MAX)
#define LONG_LONG_MAX LONGLONG_MAX
#endif

#if defined(UFWISSL_LFS)

#define ufwissl_lseek lseek64
#define FMT_NE_OFF_T UFWISSL_FMT_OFF64_T
#define UFWISSL_OFFT_MAX LONG_LONG_MAX
#ifdef HAVE_STRTOLL
#define ufwissl_strtoff strtoll
#else
#define ufwissl_strtoff strtoq
#endif

#else				/* !UFWISSL_LFS */

#define ufwissl_lseek lseek
#define FMT_NE_OFF_T UFWISSL_FMT_OFF_T

#if defined(SIZEOF_LONG_LONG) && defined(LONG_LONG_MAX) \
    && SIZEOF_OFF_T == SIZEOF_LONG_LONG
#define UFWISSL_OFFT_MAX LONG_LONG_MAX
#else
#define UFWISSL_OFFT_MAX LONG_MAX
#endif

#if SIZEOF_OFF_T > SIZEOF_LONG && defined(HAVE_STRTOLL)
#define ufwissl_strtoff strtoll
#elif SIZEOF_OFF_T > SIZEOF_LONG && defined(HAVE_STRTOQ)
#define ufwissl_strtoff strtoq
#else
#define ufwissl_strtoff strtol
#endif
#endif				/* UFWISSL_LFS */

#endif				/* UFWISSL_INTERNAL_H */
