WS-Discovery in Python
======================
This is WS-Discovery implementation for Python 3. It allows to both discover
services and publish discoverable services.

Extensive [package documentation](https://koodaamo.github.io/python-ws-discovery) is available.

Basic usage
------------

A simple `wsdiscover` command-line client is provided for discovering WS-Discovery compliant devices and systems. Run `wsdiscover --help` for usage instructions.

Here's an example of how to use the package in your Python code. The following code first publishes a service and then discovers it:

```python
    from wsdiscovery import WSDiscovery, QName, Scope

    wsd = WSDiscovery()
    wsd.start()

    ttype = QName("abc", "def")

    ttype1 = QName("namespace", "myTestService")

    # Note: some devices scope services using onvif:// scheme, not http://
    scope1 = Scope("http://myscope")
    ttype2 = QName("namespace", "myOtherTestService_type1")
    scope2 = Scope("http://other_scope")

    xAddr = "localhost:8080/abc"
    wsd.publishService(types=[ttype], scopes=[scope2], xAddrs=[xAddr])

    #ret = wsd.searchServices(scopes=[scope1], timeout=10)
    ret = wsd.searchServices()

    for service in ret:
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

