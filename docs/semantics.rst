===============================
WS-Discovery message semantics
===============================

WS-Discovery defines the following **message semantics** for managing and  discovering
the availability of networked services.

See :doc:`terms` for explanation of some common terms.

.. glossary::

   Hello
      A service *must* send a one-way multicast Hello message when it joins a network,
      or its metadata changes.

   Probe
      To discover services, optionally limited to a particular service type or scope,
      a client sends a Probe message. Probe can be unicast or multicast.

   Probe match
      When a service receives a matching Probe, it *must* respond with a Probe Match message.

   Resolve
      A client may send a one-way multicast Resolve message to locate service
      address(es).

   Resolve match
      When a service matches a Resolve message, it *must* respond with a unicast
      Resolve Match message.

   Bye
      A service *should* send a one-way multicast Bye message when preparing to
      leave a network.
