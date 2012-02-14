Multisite transport component
=============================

Introduction
------------

The MultiSite component is used to link two or more NuCentral, and call remote
services.

Protocol used is HTTPS/XML-RPC, and is bi-directionnal::

    .-------------------.       __________________________
    | NuCentral1        |      /   callService (XML-RPC)  \
    |-------------.-----|     /                  .-----.---\--------.
    |   MultiSite |HTTPS|/___/           _______\|HTTPS| MultiSite  |
    '-------\-----'-----'\              /       /|-----'------------|
             \                         /         |       NuCentral2 |
              \_______________________/          '------------------'
                callService (XML-RPC)


To enable the multisite mode, just enable the nucentral.multisite.transport module::
    # nucentral_enmod multisite_transport

Configuration file
------------------

Each server may have a configuration file in storage.

There are a main section which describes my own server configuration::

    `- self
       |- address = 10.8.0.1
       |- port = 54321
       |- ssl_cert = -----BEGIN CERTIFICATE-----
       |- ssl_key = -----BEGIN RSA PRIVATE KEY-----
       `- ssl_ca = -----BEGIN CERTIFICATE-----

MultiSite component will bind on *address* and *port*.

Each remote servers may have a section, with name is in form
Server:server_name::

    `- remotes
       |- NuCentral1
       |  |- address = 10.8.0.2
       |  `- port = 54321
       :

The server name used in section name will be used to identify the server.

Remote calls convention
-----------------------

To call a remote service, use::

    multisite.callRemote(server, component, service, ...)

NuCentral1 create a session on the remote server for you, send your
authentication information, keep cookie in your local server session,
and call the remote service.
