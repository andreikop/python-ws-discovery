"""Generic networking-agnostic WS-Discovery messaging daemon mixin implementation."""

import random
import time
import uuid
import logging

from .actions import *
from .uri import URI
from .service import Service
from .envelope import SoapEnvelope
from .udp import UNICAST_UDP_REPEAT, MULTICAST_UDP_REPEAT

APP_MAX_DELAY = 500 # miliseconds

logger = logging.getLogger("daemon")


class Daemon:
    "generic WS-Discovery messaging daemon implementation"

    def __init__(self, uuid_=None, capture=None, ttl=1, **kwargs):

        # track existence of a possible discovery proxy
        self._dpActive = False
        self._dpAddr = None
        self._dpEPR = None

        if uuid_ is not None:
            self.uuid = uuid_
        else:
            self.uuid = uuid.uuid4().urn

        self._capture = capture
        self.ttl = ttl
        self._unicast_num = kwargs.get('unicast_num', UNICAST_UDP_REPEAT)
        self._multicast_num = kwargs.get('multicast_num', MULTICAST_UDP_REPEAT)

        super().__init__(**kwargs)

    def envReceived(self, env, addr):
        action = env.getAction()
        action_name = '_handle_' + action[action.rfind('/')+1:].lower()
        try:
            handler = getattr(self, action_name)
        except AttributeError:
            logger.warning("could not find handler for: %s" % action_name)
        else:
            handler(env, addr)

    def _sendResolveMatch(self, service, relatesTo, addr):
        env = constructResolveMatch(service, relatesTo)
        self.sendUnicastMessage(env, addr[0], addr[1], unicast_num=self._unicast_num)

    def _sendProbeMatch(self, services, relatesTo, addr):
        env = constructProbeMatch(services, relatesTo)
        self.sendUnicastMessage(env, addr[0], addr[1], random.randint(0, APP_MAX_DELAY),
                                unicast_num=self._unicast_num)

    def _sendProbe(self, types=None, scopes=None, address=None, port=None):
        env = constructProbe(types, scopes)
        if self._dpActive:
            self.sendUnicastMessage(env, self._dpAddr[0], self._dpAddr[1],
                                    unicast_num=self._unicast_num)
        elif address and port:
            self.sendUnicastMessage(env, address, port,
                                    unicast_num=self._unicast_num)
        else:
            self.sendMulticastMessage(env, multicast_num=self._multicast_num)

    def _sendResolve(self, epr):
        env = constructResolve(epr)
        if self._dpActive:
            self.sendUnicastMessage(env, self._dpAddr[0], self._dpAddr[1],
                                    unicast_num=self._unicast_num)
        else:
            self.sendMulticastMessage(env, multicast_num=self._multicast_num)

    def _sendHello(self, service):
        env = constructHello(service)
        random.seed((int)(time.time() * 1000000))
        self.sendMulticastMessage(env,initialDelay=random.randint(0, APP_MAX_DELAY),
                                  multicast_num=self._multicast_num)

    def _sendBye(self, service):
        env = constructBye(service)
        service.incrementMessageNumber()
        self.sendMulticastMessage(env, multicast_num=self._multicast_num)
