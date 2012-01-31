from nucentral.backend import Component

class Hello(Component):
    """
    Hello World component saying "Hello <login>!"
    """
    NAME = "hello"
    VERSION = "1.0"
    API_VERSION = 2
    ACLS = {'users' : ('hello',)}

    def service_hello(self, context):
        return "Hello %s!" % context.user.login
