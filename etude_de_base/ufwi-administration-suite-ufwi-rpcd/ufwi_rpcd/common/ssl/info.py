from M2Crypto import m2

class SSLInfo:
    """
    Informations from SSL_CTX_set_info_callback().
    """
    def __init__(self, where, ret, ssl_ptr):
        self.where = where
        self.ret = ret
        self.ssl_ptr = ssl_ptr

    def isLoop(self):
        return self.where & m2.SSL_CB_LOOP

    def isExit(self):
        return self.where & m2.SSL_CB_EXIT

    def isAlert(self):
        return self.where & m2.SSL_CB_ALERT

    def isRead(self):
        return self.where & m2.SSL_CB_READ

    def isWrite(self):
        return self.where & m2.SSL_CB_WRITE

    def isHandshakeStart(self):
        return self.where & m2.SSL_CB_HANDSHAKE_START

    def isHandshakeDone(self):
        return self.where & m2.SSL_CB_HANDSHAKE_DONE

    def getType(self):
        return unicode(m2.ssl_get_alert_type_v(self.ret))

    def getDescription(self):
        return unicode(m2.ssl_get_alert_desc_v(self.ret))

    def getStatePrefix(self):
        w = self.where & ~m2.SSL_ST_MASK
        if (w & m2.SSL_ST_CONNECT):
            return "SSL connect"
        elif (w & m2.SSL_ST_ACCEPT):
            return "SSL accept"
        else:
            return "SSL state unknown"

    def getState(self):
        return m2.ssl_get_state_v(self.ssl_ptr)

    def __str__(self):
        if self.isLoop():
            return "LOOP: %s: %s" % (self.getStatePrefix(), self.getState())
        elif self.isExit():
            if not self.ret:
                return "FAILED: %s: %s" % (self.getStatePrefix(), self.getState())
            else:
                return "INFO: %s: %s" % (self.getStatePrefix(), self.getState())
        elif self.isAlert():
            if self.isRead():
                operation = 'read'
            else:
                operation = 'write'
            return ("ALERT: %s: %s: %s" % \
                (operation, self.getType(), self.getDescription()))
        elif self.isHandshakeStart():
            return "Handshake start"
        elif self.isHandshakeDone():
            return "Handshake done"
        else:
            return "unknown state"

    def logInto(self, logger):
        if self.isAlert():
            description = self.getDescription()
            if self.isRead():
                operation = "read"
            else:
                operation = "write"
            if description == 'close notify':
                func = logger.debug
            else:
                func = logger.critical
            # FIXME: display IP address, but how? get fd?
            #    bio_ptr = m2.ssl_get_rbio(self.ssl_ptr)
            #    fd = m2.bio_get_fd(bio_ptr)
            # M2Crypto doesn't have ssl_get_rbio() binding :-(
            func("SSL %s alert: %s" % (operation, description))
        elif self.isHandshakeStart() or self.isHandshakeDone():
            message = unicode(self)
            logger.debug(message)

