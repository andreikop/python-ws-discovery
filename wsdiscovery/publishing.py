"""Publisher application."""

import logging
import random
import time
import uuid

from .actions import *
from .uri import URI
from .util import filterServices, _generateInstanceId
from .service import Service
from .threaded import ThreadedNetworking
from .daemon import Daemon


class Publishing:
    "networking-agnostic generic service publishing mixin"

    def __init__(self, **kwargs):
        self._localServices = {}
        super().__init__(**kwargs)

    def _handle_probe(self, env, addr):
        "handle NS_ACTION_PROBE"
        services = filterServices(list(self._localServices.values()), env.getTypes(), env.getScopes())
        self._sendProbeMatch(services, env.getMessageId(), addr)

    def _handle_resolve(self, env, addr):
        "handle NS_ACTION_RESOLVE"
        if env.getEPR() in self._localServices:
            service = self._localServices[env.getEPR()]
            self._sendResolveMatch(service, env.getMessageId(), addr)


    def  _networkAddressAdded(self, addr):
        self.addSourceAddr(addr)
        for service in list(self._localServices.values()):
            self._sendHello(service)

    def _networkAddressRemoved(self, addr):
        self.removeSourceAddr(addr)


    def publishService(self, types, scopes, xAddrs):
        """Publish a service with the given TYPES, SCOPES and XAddrs (service addresses)

        if xAddrs contains item, which includes {ip} pattern, one item per IP address will be sent
        """

        if not self._serverStarted:
            raise Exception("Server not started")

        instanceId = _generateInstanceId()

        service = Service(types, scopes, xAddrs, self.uuid, instanceId)
        self._localServices[self.uuid] = service
        self._sendHello(service)


    def clearLocalServices(self):
        'send Bye messages for the services and remove them'

        for service in list(self._localServices.values()):
            self._sendBye(service)

        self._localServices.clear()

    def stop(self):
        self.clearLocalServices()


class ThreadedWSPublishing(ThreadedNetworking, Publishing, Daemon):
    "threaded service publishing"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
