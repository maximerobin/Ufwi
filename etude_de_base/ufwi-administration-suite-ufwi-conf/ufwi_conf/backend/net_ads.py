from ufwi_conf.backend.unix_service import runCommandAndCheck, RunCommandError

_TESTJOIN_COMMAND = "net ads testjoin".split()
_INFO_COMMAND = "net ads info".split()
_OK_JOIN_MSG = "Join is OK"

def net_ads_keytab_command(logger, user, password, keytab_command):
    login_string = '%'.join((user, password))
    command = "net ads -U".split()
    #slow construction, but handles spaces in login/password nicely
    command.append(login_string)
    command.append('keytab')
    command += keytab_command.split()

    command_log = "net ads -U ***user***  ***pass*** keytab %s" % keytab_command

    runCommandAndCheck(
        logger,
        command,
        env={},
        cmdstr=command_log
    )

def net_ads_testjoin(logger):
    try:
        process, stdout = runCommandAndCheck(
            logger,
            _TESTJOIN_COMMAND,
            env={},
            timeout=10
        )

    except RunCommandError:
        return False

    for line in stdout:
        if line.strip() == _OK_JOIN_MSG:
            return True

    return False

def ad_info(logger):
    data = {}

    try:
        process, stdout = runCommandAndCheck(
            logger,
            _INFO_COMMAND,
            env={},
            timeout=10
        )

    except RunCommandError:
        return data

    for line in stdout:
        split_value = line.split(":", 1)
        if len(split_value) == 2:
            key, value = split_value
            data[key] = value.strip()

    return data

