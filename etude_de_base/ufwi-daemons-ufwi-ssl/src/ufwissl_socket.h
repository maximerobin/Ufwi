/*
 ** Copyright (C) 2007-2009 INL
 ** Written by S.Tricaud <stricaud@inl.fr>
 **            L.Defert <ldefert@inl.fr>
 ** INL http://www.inl.fr/
 **
 ** NuSSL: OpenSSL / GnuTLS layer based on libneon
 */


/*
   socket handling interface
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

#ifndef UFWISSL_SOCKET_H
#define UFWISSL_SOCKET_H

#include <sys/types.h>

#include "ufwissl_defs.h"
#include "ufwissl_ssl.h"		/* for ufwissl_ssl_context */

/* Socket read timeout */
#define SOCKET_READ_TIMEOUT 120

UFWISSL_BEGIN_DECLS
/* ufwissl_socket represents a TCP socket. */
typedef struct ufwissl_socket_s ufwissl_socket;

/* ufwissl_sock_addr represents an address object. */
typedef struct ufwissl_sock_addr_s ufwissl_sock_addr;

#ifndef UFWISSL_INET_ADDR_DEFINED
typedef struct ufwissl_inet_addr_s ufwissl_inet_addr;
#endif

/* Perform process-global initialization of any libraries in use.
 * Returns non-zero on error. */
int ufwissl_sock_init(void);

/* Perform process-global shutdown of any libraries in use.  This
 * function only has effect when it has been called an equal number of
 * times to ufwissl_sock_init() for the process. */
void ufwissl_sock_exit(void);

/* Resolve the given hostname.  'flags' must be zero.  Hex
 * string IPv6 addresses (e.g. `::1') may be enclosed in brackets
 * (e.g. `[::1]'). */
ufwissl_sock_addr *ufwissl_addr_resolve(const char *hostname, int flags);

/* Returns zero if name resolution was successful, non-zero on
 * error. */
int ufwissl_addr_result(const ufwissl_sock_addr * addr);

/* Returns the first network address associated with the 'addr'
 * object.  Undefined behaviour if ufwissl_addr_result returns non-zero for
 * 'addr'; otherwise, never returns NULL.  */
const ufwissl_inet_addr *ufwissl_addr_first(ufwissl_sock_addr * addr);

/* Returns the next network address associated with the 'addr' object,
 * or NULL if there are no more. */
const ufwissl_inet_addr *ufwissl_addr_next(ufwissl_sock_addr * addr);

/* NB: the pointers returned by ufwissl_addr_first and ufwissl_addr_next are
 * valid until ufwissl_addr_destroy is called for the corresponding
 * ufwissl_sock_addr object.  They must not be passed to ufwissl_iaddr_free. */

/* If name resolution fails, copies the error string into 'buffer',
 * which is of size 'bufsiz'.  'buffer' is returned. */
char *ufwissl_addr_error(const ufwissl_sock_addr * addr, char *buffer,
		       size_t bufsiz);

/* Destroys an address object created by ufwissl_addr_resolve. */
void ufwissl_addr_destroy(ufwissl_sock_addr * addr);

/* Network address type; IPv4 or IPv6 */
typedef enum {
	ufwissl_iaddr_ipv4 = 0,
	ufwissl_iaddr_ipv6
} ufwissl_iaddr_type;

/* Create a network address object from raw byte representation (in
 * network byte order) of given type.  'raw' must be four bytes for an
 * IPv4 address, 16 bytes for an IPv6 address.  May return NULL if
 * address type is not supported. */
ufwissl_inet_addr *ufwissl_iaddr_make(ufwissl_iaddr_type type,
				  const unsigned char *raw);

/* Compare two network address objects i1 and i2; returns zero if they
 * are equivalent or non-zero otherwise.  */
int ufwissl_iaddr_cmp(const ufwissl_inet_addr * i1,
		    const ufwissl_inet_addr * i2);

/* Return the type of the given network address object. */
ufwissl_iaddr_type ufwissl_iaddr_typeof(const ufwissl_inet_addr * ia);

/* Print the string representation of network address 'ia' into the
 * buffer 'buffer', which is of length 'bufsiz'.  Returns 'buffer'. */
char *ufwissl_iaddr_print(const ufwissl_inet_addr * ia, char *buffer,
			size_t bufsiz);

/* Perform the reverse name lookup on network address 'ia', placing
 * the returned name in the 'buf' buffer (of length 'bufsiz') if
 * successful.  Returns zero on success, or non-zero on error. */
int ufwissl_iaddr_reverse(const ufwissl_inet_addr * ia, char *buf,
			size_t bufsiz);

/* Destroy a network address object created using ufwissl_iaddr_make. */
void ufwissl_iaddr_free(ufwissl_inet_addr * addr);

/* Create a socket object; returns NULL on error. */
ufwissl_socket *ufwissl_sock_create(void);

/* Create a socket object from a file descriptor; returns NULL on error. */
ufwissl_socket *ufwissl_sock_create_with_fd(int fd);

/* Specify an address to which the local end of the socket will be
 * bound during a subsequent ufwissl_sock_connect() call.  If the address
 * passed to ufwissl_sock_connect() is of a different type (family) to
 * 'addr', 'addr' is ignored.  Either 'addr' may be NULL, to use the
 * given port with unspecified address, or 'port' may be 0, to use the
 * given address with an unspecified port.
 *
 * (Note: This function is not equivalent to a BSD socket bind(), it
 * only takes effect during the _connect() call). */
void ufwissl_sock_prebind(ufwissl_socket * sock, const ufwissl_inet_addr * addr,
			unsigned int port);

/* Connect the socket to server at address 'addr' on port 'port'.
 * Returns zero on success, UFWISSL_SOCK_TIMEOUT if a timeout occurs when a
 * non-zero connect timeout is configured (and is supported), or
 * UFWISSL_SOCK_ERROR on failure.  */
int ufwissl_sock_connect(ufwissl_socket * sock, const ufwissl_inet_addr * addr,
		       unsigned int port);


ssize_t ufwissl_sock_read_available(ufwissl_socket * sock);

/* Read up to 'count' bytes from socket into 'buffer'.  Returns:
 *   UFWISSL_SOCK_* on error,
 *   >0 length of data read into buffer (may be less than 'count')
 */
ssize_t ufwissl_sock_read(ufwissl_socket * sock, char *buffer, size_t count);

/* Read up to 'count' bytes into 'buffer', leaving the data available
 * in the socket buffer to be returned by a subsequent call to
 * ufwissl_sock_read or ufwissl_sock_peek. Returns:
 *   UFWISSL_SOCK_* on error,
 *   >0 length of data read into buffer.
 */
ssize_t ufwissl_sock_peek(ufwissl_socket * sock, char *buffer, size_t count);

/* Block for up to 'n' seconds until data becomes available for reading
 * from the socket. Returns:
 *  UFWISSL_SOCK_* on error,
 *  UFWISSL_SOCK_TIMEOUT if no data arrives in 'n' seconds,
 *  0 if data arrived on the socket.
 */
int ufwissl_sock_block(ufwissl_socket * sock, int n);

/* Write 'count' bytes of 'data' to the socket.  Guarantees to either
 * write all the bytes or to fail.  Returns 0 on success, or UFWISSL_SOCK_*
 * on error. */
int ufwissl_sock_fullwrite(ufwissl_socket * sock, const char *data,
			 size_t count);

/* Read an LF-terminated line into 'buffer', and NUL-terminate it.
 * At most 'len' bytes are read (including the NUL terminator).
 * Returns:
 * UFWISSL_SOCK_* on error,
 * >0 number of bytes read (including NUL terminator)
 */
ssize_t ufwissl_sock_readline(ufwissl_socket * sock, char *buffer, size_t len);

/* Read exactly 'len' bytes into buffer, or fail; returns 0 on
 * success, UFWISSL_SOCK_* on error. */
ssize_t ufwissl_sock_fullread(ufwissl_socket * sock, char *buffer, size_t len);

/* Accepts a connection from listening socket 'fd' and places the
 * socket in 'sock'.  Returns zero on success or -1 on failure. */
int ufwissl_sock_accept(ufwissl_socket * sock, int fd);

/* INL: Same than ufwissl_sock_accept(), but with provide every info we have */
int ufwissl_sock_accept_full(ufwissl_socket * sock, int listener,
			   struct sockaddr *addr, socklen_t * addrlen);

/* Returns the file descriptor used for socket 'sock'. */
int ufwissl_sock_fd(const ufwissl_socket * sock);

/* Return address of peer, or NULL on error.  The returned address
 * must be destroyed by caller using ufwissl_iaddr_free. */
ufwissl_inet_addr *ufwissl_sock_peer(ufwissl_socket * sock, unsigned int *port);

/* Close the socket and destroy the socket object.  Returns zero on
 * success, or an errno value if close() failed. */
int ufwissl_sock_close(ufwissl_socket * sock);

/* Return current error string for socket. */
const char *ufwissl_sock_error(const ufwissl_socket * sock);

/* Set read timeout for socket, in seconds; must be a non-zero
 * positive integer. */
void ufwissl_sock_read_timeout(ufwissl_socket * sock, int timeout);

/* Set connect timeout for socket, in seconds; must be a positive
 * integer.  If a timeout of 'zero' is used then then no explicit
 * timeout handling will be used for ufwissl_sock_connect(), and the
 * connect call will only timeout as dictated by the TCP stack. */
void ufwissl_sock_connect_timeout(ufwissl_socket * sock, int timeout);

/* Negotiate an SSL connection on socket as an SSL server, using given
 * SSL context. */
int ufwissl_sock_accept_ssl(ufwissl_socket * sock, ufwissl_ssl_context * ctx);

/* Negotiate an SSL connection on socket as an SSL client, using given
 * SSL context.  The 'userdata' parameter is associated with the
 * underlying SSL library's socket structure for use in callbacks.
 * Returns zero on success, or non-zero on error. */
int ufwissl_sock_connect_ssl(ufwissl_socket * sock, ufwissl_ssl_context * ctx,
			   void *userdata);

/* Retrieve the session ID of the current SSL session.  If 'buf' is
 * non-NULL, on success, copies at most *buflen bytes to 'buf' and
 * sets *buflen to the exact number of bytes copied.  If 'buf' is
 * NULL, on success, sets *buflen to the length of the session ID.
 * Returns zero on success, non-zero on error. */
int ufwissl_sock_sessid(ufwissl_socket * sock, unsigned char *buf,
		      size_t * buflen);

/* Return human-readable name of SSL/TLS cipher used for connection,
 * or NULL if none.  The format of this string is not intended to be
 * fixed or parseable, but is informational only.  Return value is
 * NUL-terminated malloc-allocated string if not NULL, which must be
 * freed by the caller. */
char *ufwissl_sock_cipher(ufwissl_socket * sock);

UFWISSL_END_DECLS
#endif				/* UFWISSL_SOCKET_H */
