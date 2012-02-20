    MultiSite - Registration
    ========================

I. Preamble
-----------

This document describes the way used to connect firewalls between themselves.
Read the *multisite.rst* document for more details about the multisite
architecture.

1. Vocabulary
~~~~~~~~~~~~~

- *Master*: the main firewall used to register each others.
- *Slave*: a firewall connected to the master.
- *OTP*: One Time Password

2. Actors
~~~~~~~~~

Here is architecture for registration::


        .-----------.       .-----------.
        |   Slave   |<------|           |
        '-..--------'       |   Master  |
           \\               |           |<--.
            \\       ___    '-----------'   |
             \\_____|VPN|______||       .-------.
              \_________________|       | Admin |
                                        '-------'

II. Requiered
-------------

To begin the registration procedure, several things must be established:
- Master depends on nupki (not yet, waiting for toady...)
- Master must have openvpn installed

III. Protocol
-------------

1. Registration
~~~~~~~~~~~~~~~~~

Admin -> Master(multisite_master.register_firewall):
    Admin specifies the Slave hostname (or IP address), port, protocol, and admin password.

Master -> Slave(multisite_slave.request_registration):
    Master creates a new account for slave, with 'multisite_registration_%d' as
    username, and a random password (between 0 and 999999).
    Master sends this OTP to Slave, with the name of firewall used for
    registration, and parameters to connect to master (port and protocol).

Slave -> Master(multisite_master.register):
    Tries to login with OTP, and send a CSR for the OpenVPN certificate.
    Master creates certificate and send OpenVPN settings to Slave.
    Slave is in state REGISTERING.
    Slave launches OpenVPN and connection is established.

Slave -> Master(multisite_master.request_nucentral_crt):
    Slave sends a CSR to create a certificate for NuCentral.
    Master returns created certificate.
    Slave adds on multisite_transport a new remote server.

Slave => Master(multisite_master.hello):
    Slave is now connected on Master via OpenVPN.

Slave -> Master(multisite_master.end_registration):
    Registration is ended. OTP is removed and state is ONLINE

2. Connection state
~~~~~~~~~~~~~~~~~~~

States are:
* ONLINE
* OFFLINE
* REGISTERING
* ERROR (last error is logged)

A firewall have to send a HELLO message everytime to master to tell him it is
online. His state becomes ONLINE.

When a firewall leaves, it may send a BYE message. His state becomes BYE.

If a firewall is ONLINE and doesn't send any HELLO message two times, master
considers that there is a connection problem, or slave crashes, or something
else. His states become ERROR and error ('Connection timeout') is logged.

When an user tries to call a remote firewall, if it doesn't answer, the state
becomes ERROR and error is logged.

multisite_master provides a service *registration_failed*. If called, state
becomes ERROR and error is logged.

