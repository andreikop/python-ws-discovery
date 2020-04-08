"""Threaded networking facilities for implementing threaded WS-Discovery daemons."""

import logging
import random
import time
import uuid
import socket
import struct
import threading
import selectors

from .udp import UDPMessage
from .actions import *
from .uri import URI
from .util import _getNetworkAddrs
from .message import createSOAPMessage, parseSOAPMessage
from .service import Service


logger = logging.getLogger("threading")


BUFFER_SIZE = 0xffff
NETWORK_ADDRESSES_CHECK_TIMEOUT = 5
MULTICAST_PORT = 3702
MULTICAST_IPV4_ADDRESS = "239.255.255.250"


class _StoppableDaemonThread(threading.Thread):
    """Stoppable daemon thread.

    run() method shall exit, when self._quitEvent.wait() returned True
    """
    def __init__(self):
        self._quitEvent = threading.Event()
        super(_StoppableDaemonThread, self).__init__()
        self.daemon = True

    def schedule_stop(self):
        """Schedule stopping the thread.
        Use join() to wait, until thread really has been stopped
        """
        self._quitEvent.set()


class AddressMonitorThread(_StoppableDaemonThread):
    "trigger address change callbacks when local service addresses change"

    def __init__(self, wsd):
        self._addrs = set()
        self._wsd = wsd
        super(AddressMonitorThread, self).__init__()
        self._updateAddrs()

    def _updateAddrs(self):
        addrs = set(_getNetworkAddrs())

        disappeared = self._addrs.difference(addrs)
        new = addrs.difference(self._addrs)

        for addr in disappeared:
            self._wsd._networkAddressRemoved(addr)

        for addr in new:
            self._wsd._networkAddressAdded(addr)

        self._addrs = addrs

    def run(self):
        while not self._quitEvent.wait(NETWORK_ADDRESSES_CHECK_TIMEOUT):
            self._updateAddrs()


class NetworkingThread(_StoppableDaemonThread):
    def __init__(self, observer, capture=None):
        super(NetworkingThread, self).__init__()

        self.setDaemon(True)
        self._queue = []    # FIXME synchronisation

        self._knownMessageIds = set()
        self._iidMap = {}
        self._observer = observer
        self._capture = observer._capture
        self._seqnum = 1 # capture sequence number
        self._selector = selectors.DefaultSelector()

    @staticmethod
    def _makeMreq(addr):
        return struct.pack("4s4s", socket.inet_aton(MULTICAST_IPV4_ADDRESS), socket.inet_aton(addr))

    @staticmethod
    def _createMulticastOutSocket(addr, ttl):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setblocking(0)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
        if addr is None:
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.INADDR_ANY)
        else:
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(addr))

        return sock

    @staticmethod
    def _createMulticastInSocket():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        sock.bind(('', MULTICAST_PORT))
        sock.setblocking(0)

        return sock

    def addSourceAddr(self, addr):
        """None means 'system default'"""
        try:
            self._multiInSocket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, self._makeMreq(addr))
        except socket.error:  # if 1 interface has more than 1 address, exception is raised for the second
            pass

        sock = self._createMulticastOutSocket(addr, self._observer.ttl)
        self._multiOutUniInSockets[addr] = sock
        self._selector.register(sock, selectors.EVENT_READ)

    def removeSourceAddr(self, addr):
        try:
            self._multiInSocket.setsockopt(socket.IPPROTO_IP, socket.IP_DROP_MEMBERSHIP, self._makeMreq(addr))
        except socket.error:  # see comments for setsockopt(.., socket.IP_ADD_MEMBERSHIP..
            pass

        sock = self._multiOutUniInSockets[addr]
        self._selector.unregister(sock)
        sock.close()
        del self._multiOutUniInSockets[addr]

    def addUnicastMessage(self, env, addr, port, initialDelay=0):
        msg = UDPMessage(env, addr, port, UDPMessage.UNICAST, initialDelay)

        self._queue.append(msg)
        self._knownMessageIds.add(env.getMessageId())

    def addMulticastMessage(self, env, addr, port, initialDelay=0):
        msg = UDPMessage(env, addr, port, UDPMessage.MULTICAST, initialDelay)

        self._queue.append(msg)
        self._knownMessageIds.add(env.getMessageId())

    def run(self):
        while not self._quitEvent.is_set() or self._queue:
            self._sendPendingMessages()
            self._recvMessages()

    def _recvMessages(self):
        for key, events in self._selector.select(0):
            sock = socket.fromfd(key.fd, socket.AF_INET, socket.SOCK_DGRAM)
            try:
                data, addr = sock.recvfrom(BUFFER_SIZE)
            except socket.error as e:
                time.sleep(0.01)
                continue

            env = parseSOAPMessage(data, addr[0])

            if env is None: # fault or failed to parse
                continue

            _own_addrs = self._observer._addrsMonitorThread._addrs
            if addr[0] not in _own_addrs:
                if env.getAction() == NS_ACTION_PROBE_MATCH:
                    prms = "\n ".join((str(prm) for prm in env.getProbeResolveMatches()))
                    msg = "probe response from %s:\n --- begin ---\n%s\n--- end ---\n"
                    logger.debug(msg, addr[0], prms)

                if self._capture:
                    self._capture.write("%i RECV %s:%s\n" % (self._seqnum, addr[0], addr[1]))
                    self._capture.write(data.decode("utf-8") + "\n")
                    self._seqnum += 1

            mid = env.getMessageId()
            if mid in self._knownMessageIds:
                continue
            else:
                self._knownMessageIds.add(mid)

            iid = env.getInstanceId()
            if len(iid) > 0 and int(iid) >= 0:
                mnum = env.getMessageNumber()
                key = addr[0] + ":" + str(addr[1]) + ":" + str(iid)
                if mid is not None and len(mid) > 0:
                    key = key + ":" + mid
                if key not in self._iidMap:
                    self._iidMap[key] = iid
                else:
                    tmnum = self._iidMap[key]
                    if mnum > tmnum:
                        self._iidMap[key] = mnum
                    else:
                        continue

            self._observer.envReceived(env, addr)

    def _sendMsg(self, msg):
        data = createSOAPMessage(msg.getEnv()).encode("UTF-8")

        if msg.msgType() == UDPMessage.UNICAST:
            self._uniOutSocket.sendto(data, (msg.getAddr(), msg.getPort()))
            if self._capture:
                self._capture.write("%i SEND %s:%s\n" % (self._seqnum, msg.getAddr(), msg.getPort()))
                self._capture.write(data.decode("utf-8") + "\n")
                self._seqnum += 1
        else:
            for sock in list(self._multiOutUniInSockets.values()):
                sock.sendto(data, (msg.getAddr(), msg.getPort()))
                if self._capture:
                    self._capture.write("%i SEND %s:%s\n" % (self._seqnum, msg.getAddr(), msg.getPort()))
                    self._capture.write(data.decode("utf-8") + "\n")
                    self._seqnum += 1

    def _sendPendingMessages(self):
        """Method sleeps, if nothing to do"""
        if len(self._queue) == 0:
            time.sleep(0.1)
            return
        msg = self._queue.pop(0)
        if msg.canSend():
            self._sendMsg(msg)
            msg.refresh()
            if not (msg.isFinished()):
                self._queue.append(msg)
        else:
            self._queue.append(msg)
            time.sleep(0.01)

    def start(self):
        super(NetworkingThread, self).start()

        self._uniOutSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self._multiInSocket = self._createMulticastInSocket()
        self._selector.register(self._multiInSocket, selectors.EVENT_WRITE | selectors.EVENT_READ)

        self._multiOutUniInSockets = {}  # FIXME synchronisation

    def join(self):
        super(NetworkingThread, self).join()
        self._uniOutSocket.close()

        self._selector.unregister(self._multiInSocket)
        self._multiInSocket.close()


class ThreadedNetworking:
    "handle threaded networking start & stop, address add/remove & message sending"

    def __init__(self, **kwargs):
        self._networkingThread = None
        self._serverStarted = False
        super().__init__(**kwargs)

    def _startThreads(self):
        if self._networkingThread is not None:
            return

        self._networkingThread = NetworkingThread(self)
        self._networkingThread.start()
        logger.debug("networking thread started")
        self._addrsMonitorThread = AddressMonitorThread(self)
        self._addrsMonitorThread.start()
        logger.debug("address monitoring thread started")

    def _stopThreads(self):
        if self._networkingThread is None:
            return

        self._networkingThread.schedule_stop()
        self._addrsMonitorThread.schedule_stop()

        self._networkingThread.join()
        self._addrsMonitorThread.join()

        self._networkingThread = None

    def start(self):
        "start networking - should be called before using other methods"
        self._startThreads()
        self._serverStarted = True

    def stop(self):
        "cleans up and stops networking"
        self._stopThreads()
        self._serverStarted = False

    def addSourceAddr(self, addr):
        self._networkingThread.addSourceAddr(addr)

    def removeSourceAddr(self, addr):
        self._networkingThread.removeSourceAddr(addr)

    def sendUnicastMessage(self, env, host, port, initialDelay=0):
        "handle unicast message sending"
        self._networkingThread.addUnicastMessage(env, host, port, initialDelay)

    def sendMulticastMessage(self, env, initialDelay=0):
        "handle multicast message sending"
        self._networkingThread.addMulticastMessage(env, MULTICAST_IPV4_ADDRESS, MULTICAST_PORT, initialDelay)
