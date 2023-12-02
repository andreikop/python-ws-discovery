"""Threaded networking facilities for implementing threaded WS-Discovery daemons."""
import ipaddress
import logging
import platform
import selectors
import socket
import struct
import threading
import time
from typing import cast

from .actions import *
from .message import createSOAPMessage, parseSOAPMessage
from .udp import UDPMessage
from .util import _getNetworkAddrs, dom2Str

logger = logging.getLogger("threading")

BUFFER_SIZE = 0xffff
NETWORK_ADDRESSES_CHECK_TIMEOUT = 5
MULTICAST_PORT = 3702
MULTICAST_IPV4_ADDRESS = "239.255.255.250"
MULTICAST_IPV6_ADDRESS = "FF02::C"


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

    def __init__(self, wsd, protocol_version):
        self._addrs = set()
        self._wsd = wsd
        self._protocolVersion = protocol_version
        super(AddressMonitorThread, self).__init__()
        self._updateAddrs()

    def _updateAddrs(self):
        addrs = set(_getNetworkAddrs(self._protocolVersion))

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
    def __init__(self, observer, protocol_version):
        super(NetworkingThread, self).__init__()

        self.daemon = True
        self._queue = []  # FIXME synchronisation

        self._knownMessageIds = set()
        self._iidMap = {}
        self._observer = observer
        self._capture = observer._capture

        assert protocol_version in [socket.AF_INET, socket.AF_INET6]
        self._protocolVersion = protocol_version

        self._seqnum = 1  # capture sequence number
        self._selector = selectors.DefaultSelector()

    @staticmethod
    def _makeMreq(addr):
        if addr.version == 4:
            return struct.pack("4s4s", socket.inet_aton(MULTICAST_IPV4_ADDRESS), addr.packed)
        else:
            return struct.pack("=16si", socket.inet_pton(socket.AF_INET6, MULTICAST_IPV6_ADDRESS), int(addr.scope_id))

    def _get_inet(self):
        return socket.AF_INET if self._protocolVersion != socket.AF_INET6 else socket.AF_INET6

    def _get_multicast(self):
        return socket.IP_MULTICAST_IF if self._protocolVersion != socket.AF_INET6 else socket.IPV6_MULTICAST_IF

    def _get_ip_proto(self):
        return socket.IPPROTO_IP if self._protocolVersion != socket.AF_INET6 else socket.IPPROTO_IPV6

    def _get_ip_join(self):
        return socket.IP_ADD_MEMBERSHIP if self._protocolVersion != socket.AF_INET6 else socket.IPV6_JOIN_GROUP

    def _get_ip_leave(self):
        return socket.IP_DROP_MEMBERSHIP if self._protocolVersion != socket.AF_INET6 else socket.IPV6_LEAVE_GROUP

    def _get_multicast_ttl(self):
        return socket.IP_MULTICAST_TTL if self._protocolVersion != socket.AF_INET6 else socket.IPV6_MULTICAST_HOPS

    def _createMulticastOutSocket(self, addr, ttl):
        ip_proto = self._get_ip_proto()
        sock = socket.socket(self._get_inet(), socket.SOCK_DGRAM)
        sock.setblocking(0)
        sock.setsockopt(ip_proto, self._get_multicast_ttl(), ttl)

        if not addr:
            iface = socket.INADDR_ANY
        elif self._protocolVersion == socket.AF_INET:
            iface = addr.packed
        else:
            iface = int(addr.scope_id)

        sock.setsockopt(ip_proto, self._get_multicast(), iface)

        return sock

    def _createMulticastInSocket(self):
        sock = socket.socket(self._protocolVersion, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        if platform.system() in ["Darwin", "FreeBSD"]:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        sock.bind(('', MULTICAST_PORT))
        sock.setblocking(0)

        return sock

    def addSourceAddr(self, addr):
        """None means 'system default'"""
        try:
            self._multiInSocket.setsockopt(self._get_ip_proto(), self._get_ip_join(), self._makeMreq(addr))
        except socket.error as e:
            logger.warning(f"Interface has more than 1 address: {e}")

        sock = self._createMulticastOutSocket(addr, self._observer.ttl)
        self._multiOutUniInSockets[addr] = sock
        self._selector.register(sock, selectors.EVENT_READ)

    def removeSourceAddr(self, addr):
        try:
            self._multiInSocket.setsockopt(self._get_ip_proto(), self._get_ip_leave(), self._makeMreq(addr))
        except socket.error as e:
            logger.warning(f"Interface has more than 1 address: {e}")

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
        if self._capture:
            self.t0 = time.time()
        while not self._quitEvent.is_set() or self._queue:
            self._sendPendingMessages()
            self._recvMessages()

    def _recvMessages(self):
        for key, events in self._selector.select(0):
            if self._quitEvent.is_set():
                break

            sock = cast(socket.socket, key.fileobj)

            try:
                data, addr = sock.recvfrom(BUFFER_SIZE)
            except socket.error:
                time.sleep(0.01)
                continue

            env = parseSOAPMessage(data, addr[0])

            if env is None:  # fault or failed to parse
                if self._capture:
                    self._capture.write(
                        "%i WARNING: BAD RECV %s:%s TS=%s\n" % (self._seqnum, addr[0], addr[1], time.time() - self.t0))
                    self._capture.write(dom2Str(data))
                    self._seqnum += 1
                continue

            _own_addrs = self._observer._addrsMonitorThread_v4._addrs
            if addr[0] not in _own_addrs:
                if env.getAction() == NS_ACTION_PROBE_MATCH:
                    prms = "\n ".join((str(prm) for prm in env.getProbeResolveMatches()))
                    msg = "probe response from %s:\n --- begin ---\n%s\n--- end ---\n"
                    logger.debug(msg, addr[0], prms)

                if self._capture:
                    self._capture.write(
                        "%i RECV %s:%s TS=%s\n" % (self._seqnum, addr[0], addr[1], time.time() - self.t0))
                    self._capture.write(dom2Str(data))
                    self._seqnum += 1

            mid = env.getMessageId()
            if mid in self._knownMessageIds:
                continue  # https://github.com/andreikop/python-ws-discovery/issues/38 # TODO
            else:
                if self._capture:
                    self._capture.write("NEW KNOWN MSG IDS %s\n" % (mid))
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
                self._capture.write(
                    "%i SEND %s:%s TS=%s\n" % (self._seqnum, msg.getAddr(), msg.getPort(), time.time() - self.t0))
                self._capture.write(dom2Str(data))
                self._seqnum += 1
        else:
            for addr, sock in self._multiOutUniInSockets.items():
                try:
                    sock.sendto(data, (msg.getAddr(), msg.getPort()))
                except OSError as e:
                    # sendto will fail for interfaces that do not support multicast or are not up.
                    # An example of the first case is a wireguard vpn interface.
                    # In either case just log as debug and ignore the error.
                    logger.debug("Interface for %s does not support multicast or is not UP.\n\tOSError %s",
                                 socket.inet_ntoa(sock.getsockopt(self._get_ip_proto(), self._get_multicast(), 4)), e)
                if self._capture:
                    self._capture.write("%i SEND %s:%s iface=%s TS=%s\n" % (
                    self._seqnum, msg.getAddr(), msg.getPort(), addr, time.time() - self.t0))
                    self._capture.write(dom2Str(data))
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

        self._uniOutSocket = socket.socket(self._protocolVersion, socket.SOCK_DGRAM)

        self._multiInSocket = self._createMulticastInSocket()
        self._selector.register(self._multiInSocket, selectors.EVENT_WRITE | selectors.EVENT_READ)

        self._multiOutUniInSockets = {}  # FIXME synchronisation

    def join(self, **kwargs):
        assert self._quitEvent.is_set()
        super(NetworkingThread, self).join()

        self._selector.unregister(self._multiInSocket)
        self._uniOutSocket.close()
        self._multiInSocket.close()

        for sock in self._multiOutUniInSockets.values():
            try:
                sock.close()
            except socket.error as e:
                logger.error(e)


class ThreadedNetworking:
    "handle threaded networking start & stop, address add/remove & message sending"

    def __init__(self, **kwargs):
        self._networkingThread_v4 = None
        self._networkingThread_v6 = None
        self._addrsMonitorThread_v4 = None
        self._addrsMonitorThread_v6 = None
        self._serverStarted = False
        super().__init__(**kwargs)

    def _startThreads(self):
        if self._networkingThread_v4 is not None:
            return

        self._networkingThread_v4 = NetworkingThread(self, socket.AF_INET)
        self._networkingThread_v6 = NetworkingThread(self, socket.AF_INET6)
        self._networkingThread_v4.start()
        self._networkingThread_v6.start()
        logger.debug("networking threads started")

        self._addrsMonitorThread_v4 = AddressMonitorThread(self, socket.AF_INET)
        self._addrsMonitorThread_v6 = AddressMonitorThread(self, socket.AF_INET6)
        self._addrsMonitorThread_v4.start()
        self._addrsMonitorThread_v6.start()
        logger.debug("address monitoring threads started")

    def _stopThreads(self):
        if self._networkingThread_v4 is None:
            return

        self._networkingThread_v4.schedule_stop()
        self._addrsMonitorThread_v4.schedule_stop()
        self._networkingThread_v6.schedule_stop()
        self._addrsMonitorThread_v6.schedule_stop()

        self._networkingThread_v4.join()
        self._addrsMonitorThread_v4.join()
        self._networkingThread_v6.join()
        self._addrsMonitorThread_v6.join()

        self._networkingThread_v4 = None
        self._networkingThread_v6 = None

    def start(self):
        """start networking - should be called before using other methods"""
        self._startThreads()
        self._serverStarted = True

    def stop(self):
        """cleans up and stops networking"""
        self._stopThreads()
        self._serverStarted = False

    def addSourceAddr(self, addr):
        version = ipaddress.ip_address(addr).version
        if version == 4:
            self._networkingThread_v4.addSourceAddr(addr)
        elif version == 6:
            self._networkingThread_v6.addSourceAddr(addr)

    def removeSourceAddr(self, addr):
        version = ipaddress.ip_address(addr).version
        if version == 4:
            self._networkingThread_v4.removeSourceAddr(addr)
        elif version == 6:
            self._networkingThread_v6.removeSourceAddr(addr)

    def sendUnicastMessage(self, env, host, port, initialDelay=0):
        "handle unicast message sending"
        self._networkingThread_v4.addUnicastMessage(env, host, port, initialDelay)
        self._networkingThread_v6.addUnicastMessage(env, host, port, initialDelay)

    def sendMulticastMessage(self, env, initialDelay=0):
        "handle multicast message sending"
        self._networkingThread_v4.addMulticastMessage(env, MULTICAST_IPV4_ADDRESS, MULTICAST_PORT, initialDelay)
        self._networkingThread_v6.addMulticastMessage(env, MULTICAST_IPV6_ADDRESS, MULTICAST_PORT, initialDelay)
