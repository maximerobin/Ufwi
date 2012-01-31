#coding: utf-8

#messages:
APPLIED_COMPONENT_LIST = 'component list application completed'
ROLLED_BACK_COMPONENT_LIST = 'component list rollback completed'

COMPONENT_APPLY_FIRED = 'component application started'
COMPONENT_ROLLBACK_FIRED = 'component rollback started'

APPLY_ERROR = 'application error'
ROLLBACK_ERROR = 'rollback error'


#messages categories:
COMPONENT_LISTS = (
    APPLIED_COMPONENT_LIST,
    ROLLED_BACK_COMPONENT_LIST,
    )

COMPONENT_FIRED = (
    COMPONENT_APPLY_FIRED,
    COMPONENT_ROLLBACK_FIRED
    )

ERRORS = (
    APPLY_ERROR,
    ROLLBACK_ERROR,
)

COMPONENT_MESSAGE = 'component message'
PHASE_CHANGE = 'phase change'
GLOBAL_ERROR = 'error'     # for global phase, not specific to one component
GLOBAL_WARNING = 'warning' # for global phase, not specific to one component


ALL_MESSAGES = COMPONENT_LISTS + COMPONENT_FIRED + ERRORS \
             + (PHASE_CHANGE, COMPONENT_MESSAGE, GLOBAL_ERROR, GLOBAL_WARNING)

# phases
GLOBAL = 'global'                  # start
GLOBAL_APPLY_SKIPPED = 'apply skipped'   # end, apply skipped
GLOBAL_DONE = 'global completed'         # end, apply done successfully
APPLYING = 'applying'                    # start apply
APPLYING_DONE = 'application completed'  # apply done
ROLLING_BACK = 'rollback'                # start rollback
ROLLING_BACK_DONE = 'rollback completed' # rollback done

