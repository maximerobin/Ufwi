HIDE_SERVICE_RESULT = set((
    # Hide cookie
    'CORE.clientHello',
    'CORE.createSession',
    'session.get',
    'session.list',

    # Hide hash type
    'auth.getUser',
    'auth.listUsers',

    # Hide config
    'nulog.getConfig',
    'ufwi_ruleset.getConfig',
    'ufwi_ruleset.setConfig',
))

