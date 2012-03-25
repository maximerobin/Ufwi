ufwi-rpcd server events
=======================

 * ufwi-rpcdServerStarted(): modules are loaded and the server is ready to
   answer service calls from the network
 * sessionDestroyed(session): an user session has been destroyed
 * configModified(component_name): configuration has changed, event used for
   the HA synchronization

