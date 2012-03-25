from os import unlink
from os.path import join, exists
from ufwi_conf.common.ha_cfg import deconfigureHA
from ufwi_conf.common.netcfg_rw import deserialize
from ufwi_conf.common.net_exceptions import NetCfgError
from ufwi_rpcd.backend.exceptions import ConfigError

def prune_ha(component, manager):
    component.critical(
        "The HA configuration present in the "
        "configuration just imported will be discarded"
        )

    if prune_ha_config(manager):
        component.critical("HA discarded from configuration.xml")
    prune_ha_files(component)
    if prune_ha_net(manager):
        component.critical(
            "The HA interface in the configuration has been deconfigured"
            )

def prune_ha_config(manager):
    if not 'ha' in manager._modified_configuration:
        return False

    del manager._running_configuration['ha']
    del manager._modified_configuration['ha']
    return True

def prune_ha_files(component):
    var_dir = component.core.config.get('CORE','vardir')
    for filename in ("""
        ha_secondary.xml
        multisite_transport.xml
        ufwi_conf/ha_type
        ha_status
        ha_type
        ha.xml
        ufwi_conf/ha/IPaddresses
        ufwi_conf/ha/Routes
        """.split()
        ):
        fullpath = join(var_dir, filename)
        if not exists(fullpath):
            continue
        component.critical("unlink %s" % fullpath)
        unlink(fullpath)

def prune_ha_net(manager):
    try:
        net_serialized = manager._modified_configuration.get('network')
    except ConfigError:
        return False

    if net_serialized is None:
        return False

    netcfg = deserialize(net_serialized)

    try:
        deconfigureHA(netcfg)
    except NetCfgError:
        #nothing to do
        return False

    net_serialized = netcfg.serialize()

    for block in (manager._running_configuration, manager._modified_configuration):
        del block['network']
        block.fromDict('network', net_serialized)
    return True

