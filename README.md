WS-Discovery in Python
======================
This is WS-Discovery implementation for python.
It allows to discover services and to be discovered.

Authors and maintaining
-----------------------
[Original version](http://code.google.com/p/python-ws-discovery/) was created by L.A. Fernando <lafernando@gmail.com>

This is fork by Andrei Kopats <hlamer@tut.by> with fiew fixes applyied.

I forked this project to make my fixes available for the public. It seems like L.A. Fernando no longer interested in the project and ignores patches.
Maintaining the project is not among my priorities. If you know, that original author resumed maintaining this project - notify me, I'll drop the fork. If you want to maintain it and already **have done** something for it - let me know, I'll replace this page with redirect to your site.

Usage
-----

A sample use of the module is shown below:
```python
    from WSDiscovery import WSDiscovery

    wsd = WSDiscovery()
    wsd.start()

    ttype = QName("abc", "def")

    ttype1 = QName("namespace", "myTestService")
    scope1 = Scope("http://myscope")
    ttype2 = QName("namespace", "myOtherTestService_type1")
    scope2 = Scope("http://other_scope")
    
    xAddr = "localhost:8080/abc"
    wsd.publishService(types=[ttype], scopes=[scope2], xAddrs=[xAddr])
    
    #ret = wsd.searchServices(scopes=[scope1], timeout=10)
    ret = wsd.searchServices()
    
    for service in ret:
        print service.getEPR() + ":" + service.getXAddrs()[0]

    wsd.stop()
```

Development state
-----------------
This is not 100% complete and correct WS-Discovery implementation. It doesn't verify data, received from the network. It may crash, and even may contain security holes. 

It works for me, and should work for you. But test it carefully.

TODO
----

* Put more documentation.
