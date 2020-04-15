[![Documentation Status](https://readthedocs.org/projects/python-ws-discovery/badge/?version=latest)](https://python-ws-discovery.readthedocs.io/en/latest)

WS-Discovery in Python
======================
This is WS-Discovery implementation for Python 3. It allows to both discover
services and publish discoverable services. For Python 2 support, use the latest 1.x version
of this package.

Extensive [package documentation is available at ReadTheDocs](https://python-ws-discovery.readthedocs.io).

Basic usage
------------

A simple `wsdiscover` command-line client is provided for discovering WS-Discovery compliant devices and systems. Run `wsdiscover --help` for usage instructions.

Here's an example of how to use the package in your Python code. The following code first publishes a service and then discovers it:

```python
    from wsdiscovery.discovery import ThreadedWSDiscovery as WSDiscovery
    from wsdiscovery.publishing import ThreadedWSPublishing as WSPublishing
    from wsdiscovery import QName, Scope

    # Define type, scope & address of service
    ttype1 = QName("http://www.onvif.org/ver10/device/wsdl", "Device")
    scope1 = Scope("onvif://www.onvif.org/Model")
    xAddr1 = "localhost:8080/abc"

    # Publish the service
    wsp = WSPublishing()
    wsp.start()
    wsp.publishService(types=[ttype1], scopes=[scope1], xAddrs=[xAddr1])

    # Discover it (along with any other service out there)
    wsd = WSDiscovery()
    wsd.start()
    services = wsd.searchServices()
    for service in services:
        print(service.getEPR() + ":" + service.getXAddrs()[0])
    wsd.stop()
```

Development state
-----------------
This is not 100% complete and correct WS-Discovery implementation. It doesn't
verify data received from the network. It may crash, and might contain security
holes. No guarantees - test it carefully for your use case.

Authors and maintaining
-----------------------
Original version created by L.A. Fernando.

Code was then forked and maintained by Andrei Kopats.

Python2 support fixes by Michael Leinartas.

Python3 port done by Pieter Jordaan.

Packaging, major refactoring & command-line clients and
reStructuredText package documentation by Petri Savolainen.
