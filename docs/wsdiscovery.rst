======================
WS-Discovery in brief
======================

:abbr:`WS-Discovery (Web Services Discovery)` is a standard widely used by network
cameras and other connected devices. It is based on `SOAP over UDP`_, both unicast
& multicast.

The `WS-Discovery specification`_ defines the following message semantics for
managing and  discovering availability of networked services (see :doc:`glossary`
for explanation of terms used).

.. glossary::

   Hello
      A service *must* send a one-way multicast Hello message when it joins a network,
      or its metadata changes.

   Probe
      To discover services, optionally limited to a particular service type or scope,
      a client sends a Probe message. Probe can be unicast or multicast.

   Probe match
      When a service receives a matching Probe, it *must* respond with a Probe Match
      message.

   Resolve
      A client may send a one-way multicast Resolve message to locate service
      address(es).

   Resolve match
      When a service matches a Resolve message, it *must* respond with a unicast
      Resolve Match message. 

   Bye
      A service *should* send a one-way multicast Bye message when preparing to
      leave a network.

For explanations of WS-Discovery terms, see :doc:`glossary`.

.. _`SOAP over UDP`: http://docs.oasis-open.org/ws-dd/soapoverudp/1.1/wsdd-soapoverudp-1.1-spec.html
.. _`WS-Discovery specification`: http://docs.oasis-open.org/ws-dd/discovery/1.1/wsdd-discovery-1.1-spec.html
