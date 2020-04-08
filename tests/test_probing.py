import logging
import selectors
import socket
from .fixtures import probe_response
from wsdiscovery.threaded import NetworkingThread, MULTICAST_PORT
from wsdiscovery import WSDiscovery


def test_probing(monkeypatch, probe_response):
    "mock up socket registration, event selection & socket message response"

    sck = None

    def mock_register(selector, rsock, evtmask):
        """get hold of the multicast socket that will send the Probe message,
        when the socket is registered with the selector"""
        global sck
        # The Probe is sent multicast, we use that to identify the right socket.
        # Identification could be done better, but this is enough for now.
        if rsock.getsockname()[1] == MULTICAST_PORT:
            sck = rsock

    def mock_select(*args):
        "set a mock Probe response event in motion for the same socket"
        global sck
        if sck and sck.getsockname()[1] == MULTICAST_PORT:
            key = selectors.SelectorKey(sck.makefile(), sck.fileno(), [], "")
            # to mock just one response we just nullify the sock
            sck = None
            return [(key, selectors.EVENT_READ)]
        else:
            return []

    def mock_recvfrom(*args):
        return probe_response

    monkeypatch.setattr(selectors.DefaultSelector, "register", mock_register)
    monkeypatch.setattr(selectors.DefaultSelector, "select", mock_select)
    monkeypatch.setattr(socket.socket, "recvfrom", mock_recvfrom)

    # we cannot use a fixture that'd start discovery for us, since the socket
    # selector registration happens at startup time
    wsd = WSDiscovery()
    wsd.start()
    found = wsd.searchServices()

    assert len(found) == 1
    assert probe_response[1] in found[0].getXAddrs()[0]
    assert len(found[0].getScopes()) == 4
