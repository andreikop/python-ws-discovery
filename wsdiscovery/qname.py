"""Qualified name support; see e.g. https://en.wikipedia.org/wiki/QName"""


class QName:
    "Qualified name implementation"

    def __init__(self, namespace, localname, namespace_prefix=None):
        self._namespace = namespace
        self._localname = localname
        self._namespace_prefix = namespace_prefix

    def getNamespace(self):
        return self._namespace

    def getLocalname(self):
        return self._localname

    def getNamespacePrefix(self):
        return self._namespace_prefix

    def getFullname(self):
        return self.getNamespace() + ":" + self.getLocalname()

    def __repr__(self):
        return self.getFullname()



