from ufwi_rpcd.common.error import NUCONF
from ufwi_rpcd.backend import ComponentError
from ufwi_conf.common.error import NUCONF_TOOLS

class ToolsError(ComponentError):
    def __init__(self, *args, **kw):
        ComponentError.__init__(self, NUCONF, NUCONF_TOOLS, *args, **kw)

class CreateDiagFailed(ToolsError):
    def __init__(self, *args, **kw):
        ToolsError.__init__(self, CREATE_DIAG_FAILED, *args, **kw)

# Error codes:
CREATE_DIAG_FAILED = 1
