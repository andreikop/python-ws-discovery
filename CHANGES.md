Changelog
==========

2.0.0 (2020-04-16)
-------------------

- decoupled threaded networking from ws-discovery implementation
- refactored app-level discovery & publishing code into their own modules
- refactored message construction, serialization & deserialization
- added new ``wspublish`` command-line client to publish a service
- added unicast discovery support to ``wsdiscover``command-line client
- collected all namespaces in one module
- improved README example
- good documentation in reStructuredText with Sphinx
- removed Python 2 support code

1.1.2 (2019-01-01)
-------------------

- Refactoring & Python2 fixes
- Introduce automated Travis testing

1.1.1 (2018-12-21)
-------------------

- Fix packaging

1.1.0 (2018-12-21)
-------------------

- Add a simple command-line client (petri)
- Debugging support, including message capture (petri)
- Fix breakage caused by refactoring (petri)
- Simple tests (petri)

1.0.0 (2018-12-18)
-------------------

- Improved packaging (petri)
- Modularize & refactor (petri)
- Better Python2 support (mleinart)

0.2 (2017-05-19)
-----------------

- First release @pypi (petri)
