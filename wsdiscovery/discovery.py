"""Discovery application."""

import time
import uuid

from .actions import *
from .uri import URI
from .util import matchesFilter, filterServices, extractSoapUdpAddressFromURI
from .service import Service
from .namespaces import NS_DISCOVERY
from .threaded import ThreadedNetworking
from .daemon import Daemon


class Discovery:
    "networking-agnostic generic remote service discovery mixin"

    def __init__(self, **kwargs):
        self._remoteServices = {}
        self._remoteServiceHelloCallback = None
        self._remoteServiceHelloCallbackTypesFilter = None
        self._remoteServiceHelloCallbackScopesFilter = None
        self._remoteServiceByeCallback = None
        super().__init__(**kwargs)

    def setRemoteServiceHelloCallback(self, cb, types=None, scopes=None):
        """Set callback, which will be called when new service appeared online
        and sent Hi message

        typesFilter and scopesFilter might be list of types and scopes.
        If filter is set, callback is called only for Hello messages,
        which match filter

        Set None to disable callback
        """
        self._remoteServiceHelloCallback = cb
        self._remoteServiceHelloCallbackTypesFilter = types
        self._remoteServiceHelloCallbackScopesFilter = scopes

    def setRemoteServiceByeCallback(self, cb):
        """Set callback, which will be called when new service appeared online
        and sent Hi message
        Service is passed as a parameter to the callback
        Set None to disable callback
        """
        self._remoteServiceByeCallback = cb

    def setRemoveServiceDisappearedCallback(self, cb):
        """Set callback, which will be called when new service disappears
        Service uuid is passed as a parameter to the callback
        Set None to disable callback
        """
        self._remoteServiceDisppearedCallback = cb

    # discovery-related message handlers:

    def _handle_probematches(self, env, addr):
        for match in env.getProbeResolveMatches():
            self._addRemoteService(Service(match.getTypes(), match.getScopes(), match.getXAddrs(), match.getEPR(), 0))
            if match.getXAddrs() is None or len(match.getXAddrs()) == 0:
                self._sendResolve(match.getEPR())

    def _handle_resolvematches(self, env, addr):
        for match in env.getProbeResolveMatches():
            self._addRemoteService(Service(match.getTypes(), match.getScopes(), match.getXAddrs(), match.getEPR(), 0))

    def _handle_hello(self, env, addr):
        #check if it is from a discovery proxy
        rt = env.getRelationshipType()
        if rt is not None and rt.getLocalname() == "Suppression" and rt.getNamespace() == NS_DISCOVERY:
            xAddr = env.getXAddrs()[0]
            #only support 'soap.udp'
            if xAddr.startswith("soap.udp:"):
                self._dpActive = True
                self._dpAddr = extractSoapUdpAddressFromURI(URI(xAddr))
                self._dpEPR = env.getEPR()

        service = Service(env.getTypes(), env.getScopes(), env.getXAddrs(), env.getEPR(), 0)
        self._addRemoteService(service)
        if self._remoteServiceHelloCallback is not None:
            if matchesFilter(service,
                             self._remoteServiceHelloCallbackTypesFilter,
                             self._remoteServiceHelloCallbackScopesFilter):
                self._remoteServiceHelloCallback(service)

    def _handle_bye(self, env, addr):
        #if the bye is from discovery proxy... revert back to multicasting
        if self._dpActive and self._dpEPR == env.getEPR():
            self._dpActive = False
            self._dpAddr = None
            self._dpEPR = None

        self._removeRemoteService(env.getEPR())
        if self._remoteServiceByeCallback is not None:
            self._remoteServiceByeCallback(env.getEPR())


    # handle local address changes:

    def  _networkAddressAdded(self, addr):
        self.addSourceAddr(addr)

    def _networkAddressRemoved(self, addr):
        self.removeSourceAddr(addr)

    # search for & keep track of discovered remote services:

    def _addRemoteService(self, service):
        self._remoteServices[service.getEPR()] = service

    def _removeRemoteService(self, epr):
        if epr in self._remoteServices:
            del self._remoteServices[epr]

    def clearRemoteServices(self):
        'clears remotely discovered services'

        self._remoteServices.clear()

    def searchServices(self, types=None, scopes=None, address=None, port=None, timeout=3):
        'search for services given the TYPES and SCOPES in a given TIMEOUT'
        try:
            self._sendProbe(types, scopes, address, port)
        except:
            raise Exception("Server not started")

        time.sleep(timeout)

        return filterServices(list(self._remoteServices.values()), types, scopes)

    def stop(self):
        self.clearRemoteServices()


class ThreadedWSDiscovery(Daemon, Discovery, ThreadedNetworking):
    "Full threaded service discovery implementation"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def stop(self):
        super().stop()

