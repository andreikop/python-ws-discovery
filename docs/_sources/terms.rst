WS-Discovery terms
===================

.. glossary::


   Action
       In WS-Addressing, Action (URI) identifies the semantics of the message.

   QName
       A name used in XML is uniquely qualified when it's associated with a
       namespace (URI) it belongs to. This package provides a :doc:`qname`
       implementation.

   Scope
      Scopes are common identifiers used for organizing web services into
      logical groups, serving a purpose similar to that of categories or tags.
      This package provides a :doc:`scope` implementation.

   EPR
      An Endpoint reference is an :abbr:`URI (Uniform Resource Identifier)`
      that identifies a SOAP resource such as a WS-Discovery service. A
      EPR is included in a :term:`Probe match` message. A :term:`Resolve`
      message can then be used to retrieve actual network address for service.

   Envelope
      SOAP messages are wrapped in so-called envelopes. This package provides
      a :doc:`envelope` implementation.
