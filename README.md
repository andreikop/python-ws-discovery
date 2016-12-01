WS-Discovery in Python
======================
This is WS-Discovery implementation for Python2 and Python3 again.
It allows to discover services and to be discovered.

Authors and maintaining
-----------------------

[This fork](https://github.com/jn0/python-ws-discovery) is to allow Python2 mostly...

[Original version](http://code.google.com/p/python-ws-discovery/) was created by L.A. Fernando <lafernando@gmail.com>

This is fork by Andrei Kopats <hlamer@tut.by> with few fixes applied. Python3 port done by Pieter Jordaan <pieterwjordaanpc@gmail.com>

I forked this project to make my fixes available for the public. It seems like L.A. Fernando no longer interested in the project and ignores patches.
Maintaining the project is not among my priorities. If you know, that original author resumed maintaining this project - notify me, I'll drop the fork. If you want to maintain it and already **have done** something for it - let me know, I'll replace this page with redirect to your site.

Usage
-----

A sample use of the module is shown below:
```python
    from .WSDiscovery import WSDiscovery

    with WSDiscovery() as wsd:
        wsd.start()
        for service in wsd.searchServices():
            print(service.getEPR() + ":" + ';'.join(service.getXAddrs()))
```

Development state
-----------------
This is not 100% complete and correct WS-Discovery implementation. It doesn't verify data, received from the network. It may crash, and even may contain security holes. 

It works for me, and should work for you. But test it carefully.

TODO
----

* Put more documentation.
