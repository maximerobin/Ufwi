/*
 ** Copyright (C) 2007-2009 INL
 ** Written by S.Tricaud <stricaud@inl.fr>
 **            L.Defert <ldefert@inl.fr>
 **	       Eric Leblond <eleblond@inl.fr>
 ** INL http://www.inl.fr/
 **
 ** NuSSL: OpenSSL / GnuTLS layer based on libneon
 */


/*
   Socket handling routines
   Copyright (C) 1998-2007, Joe Orton <joe@manyfish.co.uk>,
   Copyright (C) 1999-2000 Tommi Komulainen <Tommi.Komulainen@iki.fi>
   Copyright (C) 2004 Aleix Conchillo Flaque <aleix@member.fsf.org>

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
  portions were originally under GPL in Mutt, http://www.mutt.org/
  Relicensed under LGPL for neon, http://www.webdav.org/neon/
*/

/**
 * \addtogroup NuSSL
 *
 * @{
 */

/**
 * \file ufwissl_socket.c
 * \brief Socket and I/O handling functions
 */


#include <config.h>
#include "ufwissl_config.h"

#include <stdio.h>
#include <sys/types.h>
#ifdef HAVE_SYS_TIME_H
#include <sys/time.h>
#endif
#include <sys/stat.h>
#ifdef HAVE_SYS_SOCKET_H
#include <sys/socket.h>
#endif

#ifdef UFWISSL_USE_POLL
#include <sys/poll.h>
#elif defined(HAVE_SYS_SELECT_H)
#include <sys/select.h>
#endif

#ifdef HAVE_NETINET_IN_H
#include <netinet/in.h>
#endif
#ifdef HAVE_NETINET_TCP_H
#include <netinet/tcp.h>
#endif
#ifdef HAVE_ARPA_INET_H
#include <arpa/inet.h>
#endif
#ifdef HAVE_NETDB_H
#include <netdb.h>
#endif

#ifdef WIN32
#include <winsock2.h>
#include <stddef.h>
#ifdef USE_GETADDRINFO
#include <ws2tcpip.h>
#endif
#endif

#if defined(HAVE_OPENSSL) && defined(HAVE_LIMITS_H)
#include <limits.h>		/* for INT_MAX */
#endif
#ifdef HAVE_STRING_H
#include <string.h>
#endif
#ifdef HAVE_STRINGS_H
#include <strings.h>
#endif
#ifdef HAVE_UNISTD_H
#include <unistd.h>
#endif
#ifdef HAVE_SIGNAL_H
#include <signal.h>
#endif
#ifdef HAVE_ERRNO_H
#include <errno.h>
#endif
#ifdef HAVE_STDLIB_H
#include <stdlib.h>
#endif
#ifdef HAVE_FCNTL_H
#include <fcntl.h>
#endif

#include <ev.h>

#ifdef HAVE_SOCKS_H
#include <socks.h>
#endif

#ifdef HAVE_OPENSSL
#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/pkcs12.h>	/* for PKCS12_PBE_add */
#include <openssl/rand.h>
#include <openssl/opensslv.h>	/* for OPENSSL_VERSION_NUMBER */
#endif

#ifdef HAVE_GNUTLS
#include <gnutls/gnutls.h>
#endif

#define UFWISSL_INET_ADDR_DEFINED
/* A slightly ugly hack: change the ufwissl_inet_addr definition to be the
 * real address type used.  The API only exposes ufwissl_inet_addr as a
 * pointer to an opaque object, so this should be well-defined
 * behaviour.  It avoids the hassle of a real wrapper ufwissl_inet_addr
 * structure, or losing type-safety by using void *. */
#ifdef USE_GETADDRINFO
typedef struct addrinfo ufwissl_inet_addr;
#else
typedef struct in_addr ufwissl_inet_addr;
#endif

#include "ufwissl_privssl.h"	/* MUST come after ufwissl_inet_addr is defined */

/* To avoid doing AAAA queries unless absolutely necessary, either use
 * AI_ADDRCONFIG where available, or a run-time check for working IPv6
 * support; the latter is only known to work on Linux. */
#if defined(USE_GETADDRINFO) && !defined(USE_GAI_ADDRCONFIG) && defined(__linux__)
#define USE_CHECK_IPV6
#endif

/* "Be Conservative In What You Build". */
#if defined(HAVE_FCNTL) && defined(O_NONBLOCK) && defined(F_SETFL) \
	&& defined(HAVE_GETSOCKOPT) && defined(SO_ERROR) \
	&& defined(HAVE_SOCKLEN_T) && defined(SOL_SOCKET) \
	&& defined(EINPROGRESS)
#define USE_NONBLOCKING_CONNECT
#endif

#include "ufwissl_internal.h"
#include "ufwissl_utils.h"
#include "ufwissl_string.h"
#include "ufwissl_socket.h"
#include "ufwissl_alloc.h"
#ifdef HAVE_SSPI
#include "ufwissl_sspi.h"
#endif

#if defined(__BEOS__) && !defined(BONE_VERSION)
/* pre-BONE */
#define ufwissl_close(s) closesocket(s)
#define ufwissl_errno errno
#elif defined(WIN32)
#define ufwissl_close(s) closesocket(s)
#define ufwissl_errno WSAGetLastError()
#else				/* really Unix! */
#define ufwissl_close(s) close(s)
#define ufwissl_errno errno
#endif

#ifdef WIN32
#define UFWISSL_ISRESET(e) ((e) == WSAECONNABORTED || (e) == WSAETIMEDOUT || \
			 (e) == WSAECONNRESET || (e) == WSAENETRESET)
#define UFWISSL_ISCLOSED(e) ((e) == WSAESHUTDOWN || (e) == WSAENOTCONN)
#define UFWISSL_ISINTR(e) (0)
#define UFWISSL_ISINPROGRESS(e) ((e) == WSAEWOULDBLOCK)	/* says MSDN */
#else				/* Unix */
/* Also treat ECONNABORTED and ENOTCONN as "connection reset" errors;
 * both can be returned by Winsock-based sockets layers e.g. CygWin */
#ifndef ECONNABORTED
#define ECONNABORTED ECONNRESET
#endif
#ifndef ENOTCONN
#define ENOTCONN ECONNRESET
#endif
#define UFWISSL_ISRESET(e) ((e) == ECONNRESET || (e) == ECONNABORTED || (e) == ENOTCONN)
#define UFWISSL_ISCLOSED(e) ((e) == EPIPE)
#define UFWISSL_ISINTR(e) ((e) == EINTR)
#define UFWISSL_ISINPROGRESS(e) ((e) == EINPROGRESS)
#endif

#include <stdio.h>
/* Critical I/O functions on a socket: useful abstraction for easily
 * handling SSL I/O alongside raw socket I/O. */
struct iofns {
	/* Read up to 'len' bytes into 'buf' from socket.  Return <0 on
	 * error or EOF, or >0; number of bytes read. */
	ssize_t(*sread) (ufwissl_socket * s, char *buf, size_t len);
	/* Write up to 'len' bytes from 'buf' to socket.  Return number of
	 * bytes written on success, or <0 on error. */
	ssize_t(*swrite) (ufwissl_socket * s, const char *buf, size_t len);
	/* Wait up to 'n' seconds for socket to become readable.  Returns
	 * 0 when readable, otherwise UFWISSL_SOCK_TIMEOUT or UFWISSL_SOCK_ERROR. */
	int (*readable) (ufwissl_socket * s, int n);
};

static const ufwissl_inet_addr dummy_laddr;

struct ufwissl_socket_s {
	int fd;
	unsigned int lport;
	const ufwissl_inet_addr *laddr;

	void *progress_ud;
	int rdtimeout, cotimeout;	/* timeouts */
	const struct iofns *ops;
	ufwissl_ssl_socket ssl;

	/* The read buffer: ->buffer stores byte which have been read; as
	 * these are consumed and passed back to the caller, bufpos
	 * advances through ->buffer.  ->bufavail gives the number of
	 * bytes which remain to be consumed in ->buffer (from ->bufpos),
	 * and is hence always <= RDBUFSIZ. */
	char *bufpos;
	size_t bufavail;
#define RDBUFSIZ 4096
	char buffer[RDBUFSIZ];
	/* Error string. */
	char error[192];
};

/* ufwissl_sock_addr represents an Internet address. */
struct ufwissl_sock_addr_s {
#ifdef USE_GETADDRINFO
	struct addrinfo *result, *cursor;
#else
	struct in_addr *addrs;
	size_t cursor, count;
#endif
	int errnum;
};

/* set_error: set socket error string to 'str'. */
#define set_error(s, str) ufwissl_strnzcpy((s)->error, (str), sizeof (s)->error)

/* set_strerror: set socket error to system error string for 'errnum' */
#ifdef WIN32
/* Print system error message to given buffer. */
static void print_error(int errnum, char *buffer, size_t buflen)
{
	if (FormatMessage(FORMAT_MESSAGE_FROM_SYSTEM
			  | FORMAT_MESSAGE_IGNORE_INSERTS,
			  NULL, (DWORD) errnum, 0,
			  buffer, buflen, NULL) == 0)
		ufwissl_snprintf(buffer, buflen, "Socket error %d", errnum);
}

#define set_strerror(s, e) print_error((e), (s)->error, sizeof (s)->error)
#else				/* not WIN32 */
#define set_strerror(s, e) ufwissl_strerror((e), (s)->error, sizeof (s)->error)
#endif

#ifdef HAVE_OPENSSL
/* Seed the SSL PRNG, if necessary; returns non-zero on failure. */
static int seed_ssl_prng(void)
{
	/* Check whether the PRNG has already been seeded. */
	if (RAND_status() == 1)
		return 0;

#if defined(EGD_PATH)
	UFWISSL_DEBUG(UFWISSL_DBG_SOCKET,
		    "Seeding PRNG from " EGD_PATH "...\n");
	if (RAND_egd(EGD_PATH) != -1)
		return 0;
#elif defined(ENABLE_EGD)
	{
		static const char *paths[] =
		    { "/var/run/egd-pool", "/dev/egd-pool",
			"/etc/egd-pool", "/etc/entropy"
		};
		size_t n;
		for (n = 0; n < sizeof(paths) / sizeof(char *); n++) {
			UFWISSL_DEBUG(UFWISSL_DBG_SOCKET,
				    "Seeding PRNG from %s...\n", paths[n]);
			if (RAND_egd(paths[n]) != -1)
				return 0;
		}
	}
#endif				/* EGD_PATH */

	UFWISSL_DEBUG(UFWISSL_DBG_SOCKET,
		    "No entropy source found; could not seed PRNG.\n");
	return -1;
}
#endif				/* HAVE_OPENSSL */

#ifdef USE_CHECK_IPV6
static int ipv6_disabled = 0;

/* On Linux kernels, IPv6 is typically built as a loadable module, and
 * socket(AF_INET6, ...) will fail if this module is not loaded, so
 * the slow AAAA lookups can be avoided for this common case. */
static void init_ipv6(void)
{
	int fd = socket(AF_INET6, SOCK_STREAM, 0);

	if (fd < 0)
		ipv6_disabled = 1;
	else
		close(fd);
}
#else
#define ipv6_disabled (0)
#endif

/* If init_state is N where > 0, ufwissl_sock_init has been called N times;
 * if == 0, library is not initialized; if < 0, library initialization
 * has failed. */
static int init_state = 0;

int ufwissl_sock_init(void)
{
#ifdef WIN32
	WORD wVersionRequested;
	WSADATA wsaData;
	int err;
#endif

	if (init_state > 0) {
		init_state++;
		return 0;
	} else if (init_state < 0) {
		return -1;
	}
#ifdef WIN32
	wVersionRequested = MAKEWORD(2, 2);

	err = WSAStartup(wVersionRequested, &wsaData);
	if (err != 0) {
		return init_state = -1;
	}
#ifdef HAVE_SSPI
	if (ufwissl_sspi_init() < 0) {
		return init_state = -1;
	}
#endif
#endif

#ifdef UFWISSL_HAVE_SOCKS
	SOCKSinit("ufwissl");
#endif

#if defined(HAVE_SIGNAL) && defined(SIGPIPE)
	(void) signal(SIGPIPE, SIG_IGN);
#endif

#ifdef USE_CHECK_IPV6
	init_ipv6();
#endif

	if (ufwissl__ssl_init()) {
		return init_state = -1;
	}

	init_state = 1;
	return 0;
}

void ufwissl_sock_exit(void)
{
	if (init_state > 0 && --init_state == 0) {
#ifdef WIN32
		WSACleanup();
#endif
		ufwissl__ssl_exit();

#ifdef HAVE_SSPI
		ufwissl_sspi_deinit();
#endif
	}
}

static void sock_activity_cb(struct ev_loop *loop, ev_io *w, int revents)
{

	if (revents & EV_ERROR) {
		UFWISSL_DEBUG(UFWISSL_DBG_SOCKET,
				"ssl: error in raw poll\n");
		ev_io_stop(loop, w);
		ev_unloop(loop, EVUNLOOP_ONE);
		return;
	}
	if (UFWISSL_ISINTR(ufwissl_errno)) {
		return;
	}
	if (revents & (EV_READ|EV_WRITE)) {
		ev_io_stop(loop, w);
		ev_unloop(loop, EVUNLOOP_ONE);
	}
}

static void sock_timeout_cb(struct ev_loop *loop, ev_timer *w, int revents)
{

	UFWISSL_DEBUG(UFWISSL_DBG_SOCKET,
			"ssl: timeout in ssl waiting\n");
	ev_io_stop(loop, w->data);
	ev_unloop(loop, EVUNLOOP_ONE);
	w->data = NULL;
}




/* Await readability (rdwr = 0) or writability (rdwr != 0) for socket
 * fd for secs seconds.  Returns <0 on error, zero on timeout, >0 if
 * data is available. */
static int raw_poll(int fdno, int rdwr, int secs)
{
	int ret;
	struct ev_loop *loop;
	ev_io sock_watcher;
	ev_timer timer;
	int timeout;

	if (secs == 0) {
		timeout = 1; /* reset to 1 second */
	} else {
		timeout = secs;
	}

	ret = -1;

	loop = ev_loop_new(0);
	if (rdwr == 0) {
		ev_io_init(&sock_watcher, sock_activity_cb, fdno , EV_READ);
	} else {
		ev_io_init(&sock_watcher, sock_activity_cb, fdno , EV_WRITE);
	}
	sock_watcher.data = (void *)(long)fdno;
	ev_io_start(loop, &sock_watcher);
	ev_timer_init (&timer, sock_timeout_cb, 1.0 * timeout, 0);
	timer.data = &sock_watcher;
	ev_timer_start(loop, &timer);

	ev_loop(loop, EVLOOP_ONESHOT);

	ev_loop_destroy(loop);

	if (timer.data == NULL) {
		ret = 0;
	} else {
		ret = 1;
	}

	return ret;
}

int ufwissl_sock_block(ufwissl_socket * sock, int n)
{
	if (sock->bufavail)
		return 0;
	return sock->ops->readable(sock, n);
}

/* Cast address object AD to type 'sockaddr_TY' */
#define SACAST(ty, ad) ((struct sockaddr_##ty *)(ad))

ssize_t ufwissl_sock_read_available(ufwissl_socket * sock)
{
	return sock->bufavail;
}

ssize_t ufwissl_sock_read(ufwissl_socket * sock, char *buffer, size_t buflen)
{
	ssize_t bytes;

#if 0
	UFWISSL_DEBUG(UFWISSL_DBG_SOCKET, "buf: at %d, %d avail [%s]\n",
		    sock->bufpos - sock->buffer, sock->bufavail,
		    sock->bufpos);
#endif

	if (sock->bufavail > 0) {
		/* Deliver buffered data. */
		if (buflen > sock->bufavail) {
			buflen = sock->bufavail;
		}
		memcpy(buffer, sock->bufpos, buflen);
		sock->bufpos += buflen;
		sock->bufavail -= buflen;
		return buflen;
	} else if (buflen >= sizeof sock->buffer) {
		/* No need for read buffer. */
		return sock->ops->sread(sock, buffer, buflen);
	} else {
		/* Fill read buffer. */
		bytes = sock->ops->sread(sock, sock->buffer,
				sizeof sock->buffer);
		if (bytes <= 0)
			return bytes;

		if (buflen > (size_t) bytes)
			buflen = bytes;
		memcpy(buffer, sock->buffer, buflen);
		sock->bufpos = sock->buffer + buflen;
		sock->bufavail = bytes - buflen;
		return buflen;
	}
}

ssize_t ufwissl_sock_peek(ufwissl_socket * sock, char *buffer, size_t buflen)
{
	ssize_t bytes;

	if (sock->bufavail) {
		/* just return buffered data. */
		bytes = sock->bufavail;
	} else {
		/* fill the buffer. */
		bytes =
		    sock->ops->sread(sock, sock->buffer,
				     sizeof sock->buffer);
		if (bytes <= 0)
			return bytes;

		sock->bufpos = sock->buffer;
		sock->bufavail = bytes;
	}

	if (buflen > (size_t) bytes)
		buflen = bytes;

	memcpy(buffer, sock->bufpos, buflen);

	return buflen;
}

/* Await data on raw fd in socket. */
static int readable_raw(ufwissl_socket * sock, int secs)
{
	int ret = raw_poll(sock->fd, 0, secs);

	if (ret < 0) {
		set_strerror(sock, ufwissl_errno);
		return UFWISSL_SOCK_ERROR;
	} else if (ret == 0) {
		set_error(sock, _("Read timed out"));
		return UFWISSL_SOCK_TIMEOUT;
	}
	return 0;
}

static ssize_t read_raw(ufwissl_socket * sock, char *buffer, size_t len)
{
	ssize_t ret;
	int try = 0;

	ret = readable_raw(sock, sock->rdtimeout);
	if (ret)
		return ret;

	do {
		ret = recv(sock->fd, buffer, len, 0);
	} while (ret == -1 && try++ < UFWISSL_OP_RETRY && UFWISSL_ISINTR(ufwissl_errno));

	if (ret == 0) {
		set_error(sock, _("Connection closed"));
		ret = UFWISSL_SOCK_CLOSED;
	} else if (ret < 0) {
		int errnum = ufwissl_errno;
		ret =
		    UFWISSL_ISRESET(errnum) ? UFWISSL_SOCK_RESET :
		    UFWISSL_SOCK_ERROR;
		set_strerror(sock, errnum);
	}

	return ret;
}

#define MAP_ERR(e) (UFWISSL_ISCLOSED(e) ? UFWISSL_SOCK_CLOSED : \
		   (UFWISSL_ISRESET(e) ? UFWISSL_SOCK_RESET : UFWISSL_SOCK_ERROR))

static ssize_t write_raw(ufwissl_socket * sock, const char *data,
			 size_t length)
{
	ssize_t ret;
	int try = 0;

#ifdef __QNX__
	/* Test failures seen on QNX over loopback, if passing large
	 * buffer lengths to send().  */
	if (length > 8192)
		length = 8192;
#endif

	do {
		ret = send(sock->fd, data, length, 0);
	} while (ret == -1 && try++ < UFWISSL_OP_RETRY && UFWISSL_ISINTR(ufwissl_errno));

	if (ret < 0) {
		int errnum = ufwissl_errno;
		set_strerror(sock, errnum);
		return MAP_ERR(errnum);
	}
	return ret;
}

static const struct iofns iofns_raw = { read_raw, write_raw, readable_raw };

#ifdef HAVE_OPENSSL
/* OpenSSL I/O function implementations. */
static int readable_ossl(ufwissl_socket * sock, int secs)
{
	if (SSL_pending(sock->ssl))
		return 0;
	return readable_raw(sock, secs);
}

/* SSL error handling, according to SSL_get_error(3). */
static int error_ossl(ufwissl_socket * sock, int sret)
{
	int errnum = SSL_get_error(sock->ssl, sret);
	unsigned long err;

	if (errnum == SSL_ERROR_ZERO_RETURN) {
		set_error(sock, _("Connection closed"));
		return UFWISSL_SOCK_CLOSED;
	}

	/* for all other errors, look at the OpenSSL error stack */
	err = ERR_get_error();
	if (err == 0) {
		/* Empty error stack, presume this is a system call error: */
		if (sret == 0) {
			/* EOF without close_notify, possible truncation */
			set_error(sock, _("Secure connection truncated"));
			return UFWISSL_SOCK_TRUNC;
		} else {
			/* Other socket error. */
			errnum = ufwissl_errno;
			set_strerror(sock, errnum);
			return MAP_ERR(errnum);
		}
	}

	if (ERR_reason_error_string(err)) {
		ufwissl_snprintf(sock->error, sizeof sock->error,
			       _("SSL error: %s"),
			       ERR_reason_error_string(err));
	} else {
		ufwissl_snprintf(sock->error, sizeof sock->error,
			       _("SSL error code %d/%d/%lu"), sret, errnum,
			       err);
	}

	/* make sure the error stack is now empty. */
	ERR_clear_error();
	return UFWISSL_SOCK_ERROR;
}

/* Work around OpenSSL's use of 'int' rather than 'size_t', to prevent
 * accidentally passing a negative number, etc. */
#define CAST2INT(n) (((n) > INT_MAX) ? INT_MAX : (n))

static ssize_t read_ossl(ufwissl_socket * sock, char *buffer, size_t len)
{
	int ret;
	int sslerr = 0;
	int i = 0;
	int try = 0;

	ret = readable_ossl(sock, sock->rdtimeout);
	if (ret)
		return ret;

	do {
		if (i > 0) {
			usleep(10000);
		}
		ret = SSL_read(sock->ssl, buffer, CAST2INT(len));
		if (ret < 0) {
			sslerr = SSL_get_error(sock->ssl, ret);
		}
	} while ((ret < 0) && try++ < UFWISSL_OP_RETRY && (sslerr == 2));

	if (ret <= 0) {
		ret = error_ossl(sock, ret);
	}

	return ret;
}

static ssize_t write_ossl(ufwissl_socket * sock, const char *data,
			  size_t len)
{
	int ret, ilen = CAST2INT(len);
	ret = SSL_write(sock->ssl, data, ilen);
	/* ssl.h says SSL_MODE_ENABLE_PARTIAL_WRITE must be enabled to
	 * have SSL_write return < length...  so, SSL_write should never
	 * return < length. */
	if (ret != ilen)
		return error_ossl(sock, ret);
	return ret;
}

static const struct iofns iofns_ssl = {
	read_ossl,
	write_ossl,
	readable_ossl
};

#elif defined(HAVE_GNUTLS)
static const int cert_type_priority[3] = { GNUTLS_CRT_X509, 0 };

/* Return zero if an alert value can be ignored. */
static int check_alert(ufwissl_socket * sock, ssize_t ret)
{
	const char *alert;

	if (ret == GNUTLS_E_WARNING_ALERT_RECEIVED) {
		alert = gnutls_alert_get_name(gnutls_alert_get(sock->ssl));
		UFWISSL_DEBUG(UFWISSL_DBG_SOCKET, "TLS warning alert: %s\n",
			    alert);
		return 0;
	} else if (ret == GNUTLS_E_FATAL_ALERT_RECEIVED) {
		alert = gnutls_alert_get_name(gnutls_alert_get(sock->ssl));
		UFWISSL_DEBUG(UFWISSL_DBG_SOCKET, "TLS fatal alert: %s\n",
			    alert);
		return -1;
	}
	return ret;
}

static int readable_gnutls(ufwissl_socket * sock, int secs)
{
	if (gnutls_record_check_pending(sock->ssl)) {
		return 0;
	}
	return readable_raw(sock, secs);
}

static ssize_t error_gnutls(ufwissl_socket * sock, ssize_t sret)
{
	ssize_t ret;

	switch (sret) {
	case 0:
		ret = UFWISSL_SOCK_CLOSED;
		set_error(sock, _("Connection closed"));
		break;
	case GNUTLS_E_FATAL_ALERT_RECEIVED:
		ret = UFWISSL_SOCK_ERROR;
		ufwissl_snprintf(sock->error, sizeof sock->error,
			       _("SSL alert received: %s"),
			       gnutls_alert_get_name(gnutls_alert_get
						     (sock->ssl)));
		break;
	case GNUTLS_E_UNEXPECTED_PACKET_LENGTH:
		/* It's not exactly an API guarantee but this error will
		 * always mean a premature EOF. */
		ret = UFWISSL_SOCK_TRUNC;
		set_error(sock, _("Secure connection truncated"));
		break;
	case GNUTLS_E_PUSH_ERROR:
		ret = UFWISSL_SOCK_RESET;
		set_error(sock, ("SSL socket write failed"));
		break;
	case GNUTLS_E_PULL_ERROR:
		ret = UFWISSL_SOCK_RESET;
		set_error(sock, _("SSL socket read failed"));
		break;
	default:
		ret = UFWISSL_SOCK_ERROR;
		ufwissl_snprintf(sock->error, sizeof sock->error,
			       _("SSL error: %s"), gnutls_strerror(sret));
	}
	return ret;
}

#define RETRY_GNUTLS(sock, ret) ((ret < 0) \
		&& try++ < UFWISSL_OP_RETRY \
		&& (ret == GNUTLS_E_INTERRUPTED || ret == GNUTLS_E_AGAIN \
		|| check_alert(sock, ret) == 0))

static ssize_t read_gnutls(ufwissl_socket * sock, char *buffer, size_t len)
{
	ssize_t ret;
	int try = 0;

	ret = readable_gnutls(sock, sock->rdtimeout);
	if (ret)
		return ret;

	do {
		ret = gnutls_record_recv(sock->ssl, buffer, len);
	} while (RETRY_GNUTLS(sock, ret));

	if (ret <= 0)
		ret = error_gnutls(sock, ret);

	return ret;
}

static ssize_t write_gnutls(ufwissl_socket * sock, const char *data,
			    size_t len)
{
	ssize_t ret;
	int try = 0;

	do {
		ret = gnutls_record_send(sock->ssl, data, len);
	} while (RETRY_GNUTLS(sock, ret));

	if (ret < 0)
		return error_gnutls(sock, ret);

	return ret;
}

static const struct iofns iofns_ssl = {
	read_gnutls,
	write_gnutls,
	readable_gnutls
};

#endif

int ufwissl_sock_fullwrite(ufwissl_socket * sock, const char *data, size_t len)
{
	ssize_t ret;

	do {
		ret = sock->ops->swrite(sock, data, len);
		if (ret > 0) {
			data += ret;
			len -= ret;
		}
	} while (ret > 0 && len > 0);

	return ret < 0 ? ret : 0;
}

ssize_t ufwissl_sock_readline(ufwissl_socket * sock, char *buf, size_t buflen)
{
	char *lf;
	size_t len;

	if ((lf = memchr(sock->bufpos, '\n', sock->bufavail)) == NULL
	    && sock->bufavail < RDBUFSIZ) {
		/* The buffered data does not contain a complete line: move it
		 * to the beginning of the buffer. */
		if (sock->bufavail)
			memmove(sock->buffer, sock->bufpos,
				sock->bufavail);
		sock->bufpos = sock->buffer;

		/* Loop filling the buffer whilst no newline is found in the data
		 * buffered so far, and there is still buffer space available */
		do {
			/* Read more data onto end of buffer. */
			ssize_t ret =
			    sock->ops->sread(sock,
					     sock->buffer + sock->bufavail,
					     RDBUFSIZ - sock->bufavail);
			if (ret < 0)
				return ret;
			sock->bufavail += ret;
		} while ((lf =
			  memchr(sock->buffer, '\n',
				 sock->bufavail)) == NULL
			 && sock->bufavail < RDBUFSIZ);
	}

	if (lf)
		len = lf - sock->bufpos + 1;
	else
		len = buflen;	/* fall into "line too long" error... */

	if ((len + 1) > buflen) {
		set_error(sock, _("Line too long"));
		return UFWISSL_SOCK_ERROR;
	}

	memcpy(buf, sock->bufpos, len);
	buf[len] = '\0';
	/* consume the line from buffer: */
	sock->bufavail -= len;
	sock->bufpos += len;
	return len;
}

ssize_t ufwissl_sock_fullread(ufwissl_socket * sock, char *buffer,
			    size_t buflen)
{
	ssize_t len;

	while (buflen > 0) {
		len = ufwissl_sock_read(sock, buffer, buflen);
		if (len < 0)
			return len;
		buflen -= len;
		buffer += len;
	}

	return 0;
}

#ifndef INADDR_NONE
#define INADDR_NONE ((in_addr_t) -1)
#endif

#if !defined(USE_GETADDRINFO) && !defined(WIN32) && !HAVE_DECL_H_ERRNO
/* Ancient versions of netdb.h don't export h_errno. */
extern int h_errno;
#endif

/* This implemementation does not attempt to support IPv6 using
 * gethostbyname2 et al.  */
ufwissl_sock_addr *ufwissl_addr_resolve(const char *hostname, int flags)
{
	ufwissl_sock_addr *addr = ufwissl_calloc(sizeof *addr);
#ifdef USE_GETADDRINFO
	struct addrinfo hints = { 0 };
	char *pnt;
	hints.ai_socktype = SOCK_STREAM;
	if (hostname[0] == '[' && ((pnt = strchr(hostname, ']')) != NULL)) {
		char *hn = ufwissl_strdup(hostname + 1);
		hn[pnt - hostname - 1] = '\0';
#ifdef AI_NUMERICHOST		/* added in the RFC2553 API */
		hints.ai_flags = AI_NUMERICHOST;
#endif
		hints.ai_family = AF_INET6;
		addr->errnum =
		    getaddrinfo(hn, NULL, &hints, &addr->result);
		ufwissl_free(hn);
	} else {
#ifdef USE_GAI_ADDRCONFIG	/* added in the RFC3493 API */
		hints.ai_flags = AI_ADDRCONFIG;
		hints.ai_family = AF_UNSPEC;
		addr->errnum =
		    getaddrinfo(hostname, NULL, &hints, &addr->result);
#else
		hints.ai_family = ipv6_disabled ? AF_INET : AF_UNSPEC;
		addr->errnum =
		    getaddrinfo(hostname, NULL, &hints, &addr->result);
#endif
	}
#else				/* Use gethostbyname() */
	in_addr_t laddr;
	struct hostent *hp;

	laddr = inet_addr(hostname);
	if (laddr == INADDR_NONE) {
		hp = gethostbyname(hostname);
		if (hp == NULL) {
#ifdef WIN32
			addr->errnum = WSAGetLastError();
#else
			addr->errnum = h_errno;
#endif
		} else if (hp->h_length != sizeof(struct in_addr)) {
			/* fail gracefully if somebody set RES_USE_INET6 */
			addr->errnum = NO_RECOVERY;
		} else {
			size_t n;
			/* count addresses */
			for (n = 0; hp->h_addr_list[n] != NULL; n++)
				/* noop */ ;

			addr->count = n;
			addr->addrs =
			    ufwissl_malloc(n * sizeof *addr->addrs);

			for (n = 0; n < addr->count; n++)
				memcpy(&addr->addrs[n], hp->h_addr_list[n],
				       hp->h_length);
		}
	} else {
		addr->addrs = ufwissl_malloc(sizeof *addr->addrs);
		addr->count = 1;
		memcpy(addr->addrs, &laddr, sizeof *addr->addrs);
	}
#endif
	return addr;
}

int ufwissl_addr_result(const ufwissl_sock_addr * addr)
{
	return addr->errnum;
}

const ufwissl_inet_addr *ufwissl_addr_first(ufwissl_sock_addr * addr)
{
#ifdef USE_GETADDRINFO
	addr->cursor = addr->result->ai_next;
	return addr->result;
#else
	addr->cursor = 0;
	return &addr->addrs[0];
#endif
}

const ufwissl_inet_addr *ufwissl_addr_next(ufwissl_sock_addr * addr)
{
#ifdef USE_GETADDRINFO
	struct addrinfo *ret = addr->cursor;
	if (addr->cursor)
		addr->cursor = addr->cursor->ai_next;
#else
	struct in_addr *ret;
	if (++addr->cursor < addr->count)
		ret = &addr->addrs[addr->cursor];
	else
		ret = NULL;
#endif
	return ret;
}

char *ufwissl_addr_error(const ufwissl_sock_addr * addr, char *buf,
		       size_t bufsiz)
{
#ifdef WIN32
	print_error(addr->errnum, buf, bufsiz);
#else
	const char *err;
#ifdef USE_GETADDRINFO
	/* override horrible generic "Name or service not known" error. */
	if (addr->errnum == EAI_NONAME)
		err = _("Host not found");
	else
		err = gai_strerror(addr->errnum);
#elif defined(HAVE_HSTRERROR)
	err = hstrerror(addr->errnum);
#else
	err = _("Host not found");
#endif
	ufwissl_strnzcpy(buf, err, bufsiz);
#endif				/* WIN32 */
	return buf;
}

char *ufwissl_iaddr_print(const ufwissl_inet_addr * ia, char *buf,
			size_t bufsiz)
{
#if defined(USE_GETADDRINFO) && defined(HAVE_INET_NTOP)
	const char *ret;
#ifdef AF_INET6
	if (ia->ai_family == AF_INET6) {
		struct sockaddr_in6 *in6 = SACAST(in6, ia->ai_addr);
		ret = inet_ntop(AF_INET6, &in6->sin6_addr, buf, bufsiz);
	} else
#endif
	if (ia->ai_family == AF_INET) {
		struct sockaddr_in *in = SACAST(in, ia->ai_addr);
		ret = inet_ntop(AF_INET, &in->sin_addr, buf, bufsiz);
	} else
		ret = NULL;
	if (ret == NULL)
		ufwissl_strnzcpy(buf, "[IP address]", bufsiz);
#elif defined(USE_GETADDRINFO) && defined(NI_NUMERICHOST)
	/* use getnameinfo instead for Win32, which lacks inet_ntop: */
	if (getnameinfo(ia->ai_addr, ia->ai_addrlen, buf, bufsiz, NULL, 0,
			NI_NUMERICHOST))
		ufwissl_strnzcpy(buf, "[IP address]", bufsiz);
#else				/* USE_GETADDRINFO */
	ufwissl_strnzcpy(buf, inet_ntoa(*ia), bufsiz);
#endif
	return buf;
}

int ufwissl_iaddr_reverse(const ufwissl_inet_addr * ia, char *buf,
			size_t bufsiz)
{
#ifdef USE_GETADDRINFO
	return getnameinfo(ia->ai_addr, ia->ai_addrlen, buf, bufsiz,
			   NULL, 0, 0);
#else
	struct hostent *hp;

	hp = gethostbyaddr(ia, sizeof *ia, AF_INET);
	if (hp && hp->h_name) {
		ufwissl_strnzcpy(buf, hp->h_name, bufsiz);
		return 0;
	}
	return -1;
#endif
}

void ufwissl_addr_destroy(ufwissl_sock_addr * addr)
{
#ifdef USE_GETADDRINFO
	if (addr->result)
		freeaddrinfo(addr->result);
#else
	if (addr->addrs)
		ufwissl_free(addr->addrs);
#endif
	ufwissl_free(addr);
}

/* Perform a connect() for fd to address sa of length salen, with a
 * timeout if supported on this platform.  Returns zero on success or
 * UFWISSL_SOCK_* on failure, with sock->error set appropriately. */
static int timed_connect(ufwissl_socket * sock, int fd,
			 const struct sockaddr *sa, size_t salen)
{
	int ret;

#ifdef USE_NONBLOCKING_CONNECT
	if (sock->cotimeout) {
		int errnum, flags;

		/* Get flags and then set O_NONBLOCK. */
		flags = fcntl(fd, F_GETFL);
		if (fcntl(fd, F_SETFL, flags | O_NONBLOCK) == -1) {
			set_strerror(sock, errno);
			return UFWISSL_SOCK_ERROR;
		}

		ret = connect(fd, sa, salen);
		if (ret == -1) {
			errnum = ufwissl_errno;
			if (UFWISSL_ISINPROGRESS(errnum)) {
				ret = raw_poll(fd, 1, sock->cotimeout);
				if (ret > 0) {	/* poll got data */
					socklen_t len = sizeof(errnum);

					/* Check whether there is a pending error for the
					 * socket.  Per Stevens UNPv1§15.4, Solaris will
					 * return a pending error via errno by failing the
					 * getsockopt() call. */

					errnum = 0;
					if (getsockopt
					    (fd, SOL_SOCKET, SO_ERROR,
					     &errnum, &len))
						errnum = errno;

					if (errnum == 0) {
						ret = 0;
					} else {
						set_strerror(sock, errnum);
						ret = UFWISSL_SOCK_ERROR;
					}
				} else if (ret == 0) {	/* poll timed out */
					set_error(sock,
						  _
						  ("Connection timed out"));
					ret = UFWISSL_SOCK_TIMEOUT;
				} else {	/* poll failed */

					set_strerror(sock, errno);
					ret = UFWISSL_SOCK_ERROR;
				}
			} else {	/* non-EINPROGRESS error from connect() */

				set_strerror(sock, errnum);
				ret = UFWISSL_SOCK_ERROR;
			}
		}

		/* Reset to old flags: */
		if (fcntl(fd, F_SETFL, flags) == -1) {
			set_strerror(sock, errno);
			ret = UFWISSL_SOCK_ERROR;
		}
	} else
#endif				/* USE_NONBLOCKING_CONNECT */
	{
		ret = connect(fd, sa, salen);

		if (ret < 0) {
			set_strerror(sock, errno);
			ret = UFWISSL_SOCK_ERROR;
		}
	}

	return ret;
}

/* Connect socket to address 'addr' on given 'port'.  Returns zero on
 * success or UFWISSL_SOCK_* on failure with sock->error set
 * appropriately. */
static int connect_socket(ufwissl_socket * sock, int fd,
			  const ufwissl_inet_addr * addr, unsigned int port)
{
#ifdef USE_GETADDRINFO
#ifdef AF_INET6
	/* fill in the _family field for AIX 4.3, which forgets to do so. */
	if (addr->ai_family == AF_INET6) {
		struct sockaddr_in6 in6;
		memcpy(&in6, addr->ai_addr, sizeof in6);
		in6.sin6_port = port;
		in6.sin6_family = AF_INET6;
		return timed_connect(sock, fd, (struct sockaddr *) &in6,
				     sizeof in6);
	} else
#endif
	if (addr->ai_family == AF_INET) {
		struct sockaddr_in in;
		memcpy(&in, addr->ai_addr, sizeof in);
		in.sin_port = port;
		in.sin_family = AF_INET;
		return timed_connect(sock, fd, (struct sockaddr *) &in,
				     sizeof in);
	} else {
		set_strerror(sock, EINVAL);
		return UFWISSL_SOCK_ERROR;
	}
#else
	struct sockaddr_in sa;
	sa.sin_family = AF_INET;
	sa.sin_port = port;
	sa.sin_addr = *addr;
	return timed_connect(sock, fd, (struct sockaddr *) &sa, sizeof sa);
#endif
}

ufwissl_socket *ufwissl_sock_create(void)
{
	ufwissl_socket *sock = ufwissl_calloc(sizeof *sock);
	sock->rdtimeout = SOCKET_READ_TIMEOUT;
	sock->cotimeout = 0;
	sock->bufpos = sock->buffer;
	sock->ops = &iofns_raw;
	sock->fd = -1;
	return sock;
}

/* XXX: INL Addition */
ufwissl_socket *ufwissl_sock_create_with_fd(int fd)
{
	ufwissl_socket *sock = ufwissl_sock_create();
	sock->fd = fd;
	return sock;
}


#ifdef USE_GETADDRINFO
#define ia_family(a) ((a)->ai_family)
#define ia_proto(a)  ((a)->ai_protocol)
#else
#define ia_family(a) AF_INET
#define ia_proto(a)  0
#endif

void ufwissl_sock_prebind(ufwissl_socket * sock, const ufwissl_inet_addr * addr,
			unsigned int port)
{
	sock->lport = port;
	sock->laddr = addr ? addr : &dummy_laddr;
}

/* Bind socket 'fd' to address/port 'addr' and 'port', for subsequent
 * connect() to address of family 'peer_family'. */
static int do_bind(int fd, int peer_family,
		   const ufwissl_inet_addr * addr, unsigned int port)
{
#if defined(HAVE_SETSOCKOPT) && defined(SO_REUSEADDR) && defined(SOL_SOCKET)
	{
		int flag = 1;

		(void) setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &flag,
				  sizeof flag);
		/* An error here is not fatal, so ignore it. */
	}
#endif


#ifdef USE_GETADDRINFO
	/* Use a sockaddr_in6 if an AF_INET6 local address is specifed, or
	 * if no address is specified and the peer address is AF_INET6: */
	if ((addr != &dummy_laddr && addr->ai_family == AF_INET6)
	    || (addr == &dummy_laddr && peer_family == AF_INET6)) {
		struct sockaddr_in6 in6;

		if (addr == &dummy_laddr)
			memset(&in6, 0, sizeof in6);
		else
			memcpy(&in6, addr->ai_addr, sizeof in6);
		in6.sin6_port = htons(port);
		/* fill in the _family field for AIX 4.3, which forgets to do so. */
		in6.sin6_family = AF_INET6;

		return bind(fd, (struct sockaddr *) &in6, sizeof in6);
	} else
#endif
	{
		struct sockaddr_in in;

		if (addr == &dummy_laddr)
			memset(&in, 0, sizeof in);
		else {
#ifdef USE_GETADDRINFO
			memcpy(&in, addr->ai_addr, sizeof in);
#else
			in.sin_addr = *addr;
#endif
		}
		in.sin_port = htons(port);
		in.sin_family = AF_INET;

		return bind(fd, (struct sockaddr *) &in, sizeof in);
	}
}

int ufwissl_sock_connect(ufwissl_socket * sock,
		       const ufwissl_inet_addr * addr, unsigned int port)
{
	int fd, ret;


	/* use SOCK_STREAM rather than ai_socktype: some getaddrinfo
	 * implementations do not set ai_socktype, e.g. RHL6.2. */
	fd = socket(ia_family(addr), SOCK_STREAM, ia_proto(addr));
	if (fd < 0) {
		set_strerror(sock, ufwissl_errno);
		return -1;
	}
#if !defined(UFWISSL_USE_POLL) && !defined(WIN32)
	if (fd > FD_SETSIZE) {
		ufwissl_close(fd);
		set_error(sock,
			  _
			  ("Socket descriptor number exceeds FD_SETSIZE"));
		return UFWISSL_SOCK_ERROR;
	}
#endif

#if defined(HAVE_FCNTL) && defined(F_GETFD) && defined(F_SETFD) && defined(FD_CLOEXEC)
	/* Set the FD_CLOEXEC bit for the new fd. */
	if ((ret = fcntl(fd, F_GETFD)) >= 0) {
		fcntl(fd, F_SETFD, ret | FD_CLOEXEC);
		/* ignore failure; not a critical error. */
	}
#endif

	if (sock->laddr && (sock->laddr == &dummy_laddr ||
			    ia_family(sock->laddr) == ia_family(addr))) {
		ret =
		    do_bind(fd, ia_family(addr), sock->laddr, sock->lport);
		if (ret < 0) {
			int errnum = errno;
			ufwissl_close(fd);
			set_strerror(sock, errnum);
			return UFWISSL_SOCK_ERROR;
		}
	}
#if defined(TCP_NODELAY) && defined(HAVE_SETSOCKOPT) && defined(IPPROTO_TCP)
	{			/* Disable the Nagle algorithm; better to add write buffering
				 * instead of doing this. */
		int flag = 1;
		setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &flag,
			   sizeof flag);
	}
#endif

	ret = connect_socket(sock, fd, addr, htons(port));
	if (ret == 0)
		sock->fd = fd;
	else
		ufwissl_close(fd);

	return ret;
}

ufwissl_inet_addr *ufwissl_sock_peer(ufwissl_socket * sock, unsigned int *port)
{
	union saun {
		struct sockaddr_in sin;
#ifdef USE_GETADDRINFO
		struct sockaddr_in6 sin6;
#endif
	} saun;
	socklen_t len = sizeof saun;
	ufwissl_inet_addr *ia;
	struct sockaddr *sad = (struct sockaddr *) &saun;

	if (getpeername(sock->fd, sad, &len) != 0) {
		set_strerror(sock, errno);
		return NULL;
	}

	ia = ufwissl_calloc(sizeof *ia);
#ifdef USE_GETADDRINFO
	ia->ai_addr = ufwissl_malloc(sizeof *ia);
	ia->ai_addrlen = len;
	memcpy(ia->ai_addr, sad, len);
	ia->ai_family = sad->sa_family;
#else
	memcpy(ia, &saun.sin.sin_addr.s_addr, sizeof *ia);
#endif

#ifdef USE_GETADDRINFO
	*port = ntohs(sad->sa_family == AF_INET ?
		      saun.sin.sin_port : saun.sin6.sin6_port);
#else
	*port = ntohs(saun.sin.sin_port);
#endif

	return ia;
}

ufwissl_inet_addr *ufwissl_iaddr_make(ufwissl_iaddr_type type,
				  const unsigned char *raw)
{
	ufwissl_inet_addr *ia;
#if !defined(AF_INET6) || !defined(USE_GETADDRINFO)
	/* fail if IPv6 address is given if IPv6 is not supported. */
	if (type == ufwissl_iaddr_ipv6)
		return NULL;
#endif
	ia = ufwissl_calloc(sizeof *ia);
#ifdef USE_GETADDRINFO
	/* ai_protocol and ai_socktype aren't used by connect_socket() so
	 * ignore them here. (for now) */
	if (type == ufwissl_iaddr_ipv4) {
		struct sockaddr_in *in4 = ufwissl_calloc(sizeof *in4);
		ia->ai_family = AF_INET;
		ia->ai_addr = (struct sockaddr *) in4;
		ia->ai_addrlen = sizeof *in4;
		in4->sin_family = AF_INET;
		memcpy(&in4->sin_addr.s_addr, raw,
		       sizeof in4->sin_addr.s_addr);
	}
#ifdef AF_INET6
	else {
		struct sockaddr_in6 *in6 = ufwissl_calloc(sizeof *in6);
		ia->ai_family = AF_INET6;
		ia->ai_addr = (struct sockaddr *) in6;
		ia->ai_addrlen = sizeof *in6;
		in6->sin6_family = AF_INET6;
		memcpy(&in6->sin6_addr, raw,
		       sizeof in6->sin6_addr.s6_addr);
	}
#endif
#else				/* !USE_GETADDRINFO */
	memcpy(&ia->s_addr, raw, sizeof ia->s_addr);
#endif
	return ia;
}

ufwissl_iaddr_type ufwissl_iaddr_typeof(const ufwissl_inet_addr * ia)
{
#ifdef USE_GETADDRINFO
	return ia->ai_family ==
	    AF_INET6 ? ufwissl_iaddr_ipv6 : ufwissl_iaddr_ipv4;
#else
	return ufwissl_iaddr_ipv4;
#endif
}

int ufwissl_iaddr_cmp(const ufwissl_inet_addr * i1, const ufwissl_inet_addr * i2)
{
#ifdef USE_GETADDRINFO
	if (i1->ai_family != i2->ai_family)
		return i2->ai_family - i1->ai_family;
	if (i1->ai_family == AF_INET) {
		struct sockaddr_in *in1 = SACAST(in, i1->ai_addr),
		    *in2 = SACAST(in, i2->ai_addr);
		return memcmp(&in1->sin_addr.s_addr, &in2->sin_addr.s_addr,
			      sizeof in1->sin_addr.s_addr);
	} else if (i1->ai_family == AF_INET6) {
		struct sockaddr_in6 *in1 = SACAST(in6, i1->ai_addr),
		    *in2 = SACAST(in6, i2->ai_addr);
		return memcmp(in1->sin6_addr.s6_addr,
			      in2->sin6_addr.s6_addr,
			      sizeof in1->sin6_addr.s6_addr);
	} else
		return -1;
#else
	return memcmp(&i1->s_addr, &i2->s_addr, sizeof i1->s_addr);
#endif
}

void ufwissl_iaddr_free(ufwissl_inet_addr * addr)
{
#ifdef USE_GETADDRINFO
	ufwissl_free(addr->ai_addr);
#endif
	ufwissl_free(addr);
}

int ufwissl_sock_accept(ufwissl_socket * sock, int listener)
{
	int fd = accept(listener, NULL, NULL);

	if (fd < 0)
		return -1;

	sock->fd = fd;
	return 0;
}

int ufwissl_sock_accept_full(ufwissl_socket * sock, int listener,
			   struct sockaddr *addr, socklen_t * addrlen)
{
	int fd = accept(listener, addr, addrlen);

	if (fd < 0)
		return -1;

	sock->fd = fd;
	return 0;
}

int ufwissl_sock_fd(const ufwissl_socket * sock)
{
	return sock->fd;
}

void ufwissl_sock_read_timeout(ufwissl_socket * sock, int timeout)
{
	sock->rdtimeout = timeout;
}

void ufwissl_sock_connect_timeout(ufwissl_socket * sock, int timeout)
{
	sock->cotimeout = timeout;
}

#ifdef HAVE_GNUTLS
/* Dumb server session cache implementation for GNUTLS; holds a single
 * session. */

/* Copy datum 'src' to 'dest'. */
static void copy_datum(gnutls_datum * dest, gnutls_datum * src)
{
	dest->size = src->size;
	dest->data =
	    memcpy(gnutls_malloc(src->size), src->data, src->size);
}

/* Callback to store a session 'data' with id 'key'. */
static int store_sess(void *userdata, gnutls_datum key, gnutls_datum data)
{
	ufwissl_ssl_context *ctx = userdata;

	if (ctx->cache.server.key.data) {
		gnutls_free(ctx->cache.server.key.data);
		gnutls_free(ctx->cache.server.data.data);
	}

	copy_datum(&ctx->cache.server.key, &key);
	copy_datum(&ctx->cache.server.data, &data);

	return 0;
}

/* Returns non-zero if d1 and d2 are the same datum. */
static int match_datum(gnutls_datum * d1, gnutls_datum * d2)
{
	return d1->size == d2->size
	    && memcmp(d1->data, d2->data, d1->size) == 0;
}

/* Callback to retrieve a session of id 'key'. */
static gnutls_datum retrieve_sess(void *userdata, gnutls_datum key)
{
	ufwissl_ssl_context *ctx = userdata;
	gnutls_datum ret = { NULL, 0 };

	if (match_datum(&ctx->cache.server.key, &key)) {
		copy_datum(&ret, &ctx->cache.server.data);
	}

	return ret;
}

/* Callback to remove a session of id 'key'; stub needed but
 * implementation seems unnecessary. */
static int remove_sess(void *userdata, gnutls_datum key)
{
	return -1;
}
#endif

int ufwissl_sock_accept_ssl(ufwissl_socket * sock, ufwissl_ssl_context * ctx)
{
	int ret;
	ufwissl_ssl_socket ssl;
	char errmsg[1024];

#if defined(HAVE_OPENSSL)
	ufwissl_ssl_context_set_verify(ctx, ctx->verify, NULL, NULL);
	ssl = SSL_new(ctx->ctx);

	SSL_set_fd(ssl, sock->fd);

	if (ctx->ciphers != NULL)
		SSL_set_cipher_list(ssl, ctx->ciphers);

	sock->ssl = ssl;
	errmsg[0] = '\0';
	ret = ufwissl_ssl_accept(&ssl, sock->cotimeout, errmsg, sizeof(errmsg));
	if (ret == 0) { /* timeout */
		ufwissl_snprintf(sock->error, (sizeof sock->error),
				_("SSL handshake timeout"));
		return UFWISSL_SOCK_ERROR;
	}
	if (ret != 1) {
		int ret_verif;
		ret_verif = SSL_get_verify_result(ssl);
		if (ret_verif != 0) {
			ufwissl_snprintf(sock->error, sizeof(sock->error),
					_("Error is %s\nCertificate verification: %s"),
					errmsg,
					X509_verify_cert_error_string(ret_verif));
			return UFWISSL_SOCK_ERROR;
		} else {
			ufwissl_snprintf(sock->error, sizeof(sock->error),
					_("%s"),
					errmsg);
			return UFWISSL_SOCK_ERROR;
		}

		return error_ossl(sock, ret);
	}
#elif defined(HAVE_GNUTLS)
	gnutls_init(&ssl, GNUTLS_SERVER);
	gnutls_credentials_set(ssl, GNUTLS_CRD_CERTIFICATE, ctx->cred);
	if (ctx->ciphers != NULL) {
#ifdef HAVE_GNUTLS_STRING_PRIORITY
		gnutls_priority_t prio;
		const char *err_pos;

		ret = gnutls_priority_init (&prio, ctx->ciphers, &err_pos);
		if (ret != GNUTLS_E_SUCCESS) {
			ufwissl_snprintf(sock->error, sizeof sock->error,
					_("Could not init cipher list %s: %s"),
					err_pos,
					gnutls_strerror(ret));
			return UFWISSL_SOCK_ERROR;
		}

		ret = gnutls_priority_set(ssl, prio);
		if (ret != GNUTLS_E_SUCCESS) {
			ufwissl_snprintf(sock->error, sizeof sock->error,
					_("Could not set cipher list: %s"),
					gnutls_strerror(ret));
			return UFWISSL_SOCK_ERROR;
		}

		gnutls_priority_deinit (prio);
#else /* HAVE_GNUTLS_STRING_PRIORITY */
		ufwissl_snprintf(sock->error, sizeof sock->error,
				_("GnuTLS library is too old (%s) and does not support gnutls_priority_set. Upgrade library, or comment cipherlist option."),
				gnutls_check_version(NULL));
		return UFWISSL_SOCK_ERROR;
#endif /* HAVE_GNUTLS_STRING_PRIORITY */
	} else {
		gnutls_set_default_priority(ssl);
	}

	/* Set up dummy session cache. */
	gnutls_db_set_store_function(ssl, store_sess);
	gnutls_db_set_retrieve_function(ssl, retrieve_sess);
	gnutls_db_set_remove_function(ssl, remove_sess);
	gnutls_db_set_ptr(ssl, ctx);

	gnutls_certificate_server_set_request(ssl, ctx->verify);
	gnutls_dh_set_prime_bits(ssl, ctx->dh_bits);
	sock->ssl = ssl;
	gnutls_transport_set_ptr((gnutls_session_t) sock->ssl,
				 (gnutls_transport_ptr) (long) sock->fd);

	ret = ufwissl_ssl_accept(&ssl, sock->cotimeout, errmsg, sizeof(errmsg));
	if (ret == 0) { /* timeout */
		ufwissl_snprintf(sock->error, sizeof sock->error,
				_("SSL handshake timeout"));
		return UFWISSL_SOCK_ERROR;
	}
	if (ret < 0) {
		ufwissl_snprintf(sock->error, sizeof(sock->error),
				_("%s"),
				errmsg);
		return UFWISSL_SOCK_ERROR;
	}
#if 0				/* done from session.*_post_handshake in ufwissl_gnutls.c */
	if (ctx->verify && gnutls_certificate_verify_peers(ssl)) {
		set_error(sock,
			  _("Client certificate verification failed"));
		return UFWISSL_SOCK_ERROR;
	}
#endif
#endif
	sock->ops = &iofns_ssl;
	return 0;
}

int ufwissl_sock_connect_ssl(ufwissl_socket * sock, ufwissl_ssl_context * ctx,
			   void *userdata)
{
	int ret;

#if defined(HAVE_OPENSSL)
	SSL *ssl;

	if (seed_ssl_prng()) {
		set_error(sock, _("SSL disabled due to lack of entropy"));
		return UFWISSL_SOCK_ERROR;
	}

	/* If runtime library version differs from compile-time version
	 * number in major/minor/fix level, abort soon. */
	if ((SSLeay() ^ OPENSSL_VERSION_NUMBER) & 0xFFFFF000) {
		set_error(sock,
			  _
			  ("SSL disabled due to library version mismatch"));
		return UFWISSL_SOCK_ERROR;
	}

	sock->ssl = ssl = SSL_new(ctx->ctx);
	if (!ssl) {
		set_error(sock, _("Could not create SSL structure"));
		return UFWISSL_SOCK_ERROR;
	}

	SSL_set_app_data(ssl, userdata);
	SSL_set_mode(ssl, SSL_MODE_AUTO_RETRY);
	SSL_set_fd(ssl, sock->fd);
	sock->ops = &iofns_ssl;

#ifdef SSL_set_tlsext_host_name
	if (ctx->hostname) {
		/* Try to enable SNI, but ignore failure (should only fail for
		 * >255 char hostnames, which are probably not legal
		 * anyway).  */
		if (SSL_set_tlsext_host_name(ssl, ctx->hostname) != 1) {
			ERR_clear_error();
		}
	}
#endif

	if (ctx->sess)
		SSL_set_session(ssl, ctx->sess);

	ret = SSL_connect(ssl);
	if (ret != 1) {
		error_ossl(sock, ret);
		SSL_free(ssl);
		sock->ssl = NULL;
		return UFWISSL_SOCK_ERROR;
	}
#elif defined(HAVE_GNUTLS)
	/* DH and RSA params are set in ufwissl_ssl_context_create
	 * */
	gnutls_init(&sock->ssl, GNUTLS_CLIENT);
	gnutls_set_default_priority(sock->ssl);
	gnutls_certificate_type_set_priority(sock->ssl,
					     cert_type_priority);
	gnutls_session_set_ptr(sock->ssl, userdata);
	gnutls_credentials_set(sock->ssl, GNUTLS_CRD_CERTIFICATE,
			       ctx->cred);

#ifdef XXX			/* keep or drop ? */
	if (ctx->hostname) {
		gnutls_server_name_set(sock->ssl, GNUTLS_NAME_DNS,
				       ctx->hostname,
				       strlen(ctx->hostname));
	}
#endif

	gnutls_transport_set_ptr(sock->ssl,
				 (gnutls_transport_ptr) (long) sock->fd);

	if (ctx->cache.client.data) {
#if defined(HAVE_GNUTLS_SESSION_GET_DATA2)
		gnutls_session_set_data(sock->ssl,
					ctx->cache.client.data,
					ctx->cache.client.size);
#else
		gnutls_session_set_data(sock->ssl,
					ctx->cache.client.data,
					ctx->cache.client.len);
#endif
	}
	sock->ops = &iofns_ssl;

	ret = gnutls_handshake(sock->ssl);
	if (ret < 0) {
		gnutls_deinit(sock->ssl);
		sock->ssl = NULL;
		error_gnutls(sock, ret);
		return UFWISSL_SOCK_ERROR;
	}

	if (!gnutls_session_is_resumed(sock->ssl)) {
		/* New session.  The old method of using the _get_data
		 * function seems to be broken with 1.3.0 and later*/
#if defined(HAVE_GNUTLS_SESSION_GET_DATA2)
		gnutls_session_get_data2(sock->ssl, &ctx->cache.client);
#else
		ctx->cache.client.len = 0;
		if (gnutls_session_get_data(sock->ssl, NULL,
					    &ctx->cache.client.len) == 0) {
			ctx->cache.client.data =
			    ufwissl_malloc(ctx->cache.client.len);
			gnutls_session_get_data(sock->ssl,
						ctx->cache.client.data,
						&ctx->cache.client.len);
		}
#endif
	}
#endif
	return 0;
}

ufwissl_ssl_socket ufwissl__sock_sslsock(ufwissl_socket * sock)
{
	return sock->ssl;
}

#if 0				/* Unused */
int ufwissl_sock_sessid(ufwissl_socket * sock, unsigned char *buf,
		      size_t * buflen)
{
#ifdef HAVE_GNUTLS
	if (sock->ssl) {
		return gnutls_session_get_id(sock->ssl, buf, buflen);
	} else {
		return -1;
	}
#else
	SSL_SESSION *sess;

	if (!sock->ssl) {
		return -1;
	}

	sess = SSL_get0_session(sock->ssl);

	if (!buf) {
		*buflen = sess->session_id_length;
		return 0;
	}

	if (*buflen < sess->session_id_length) {
		return -1;
	}

	*buflen = sess->session_id_length;
	memcpy(buf, sess->session_id, *buflen);
	return 0;
#endif
}
#endif

char *ufwissl_sock_cipher(ufwissl_socket * sock)
{
	if (sock->ssl) {
#ifdef HAVE_OPENSSL
		const char *name = SSL_get_cipher(sock->ssl);
		return ufwissl_strdup(name);
#elif defined(HAVE_GNUTLS)
		const char *name =
		    gnutls_cipher_get_name(gnutls_cipher_get(sock->ssl));
		return ufwissl_strdup(name);
#endif
	} else {
		return NULL;
	}
}

const char *ufwissl_sock_error(const ufwissl_socket * sock)
{
	return sock->error;
}

/* Closes given ufwissl_socket */
int ufwissl_sock_close(ufwissl_socket * sock)
{
	int ret;

#if defined(HAVE_OPENSSL)
	if (sock->ssl) {
		SSL_shutdown(sock->ssl);
		SSL_free(sock->ssl);
	}
#elif defined(HAVE_GNUTLS)
	if (sock->ssl) {
		int try = 0;
		do {
			ret = gnutls_bye(sock->ssl, GNUTLS_SHUT_RDWR);
		} while (ret < 0 && try++ < UFWISSL_OP_RETRY
			 && (ret == GNUTLS_E_INTERRUPTED
			     || ret == GNUTLS_E_AGAIN));
		gnutls_deinit(sock->ssl);
	}
#endif

	if (sock->fd < 0)
		ret = 0;
	else {
		shutdown(sock->fd, SHUT_RDWR);
		ret = ufwissl_close(sock->fd);
	}
	ufwissl_free(sock);
	return ret;
}

/** @} */
