import os
import select
import socket
from mock import patch
from wsdiscovery import WSDiscovery, QName, Scope


DISCOVER_IP =  "192.168.1.104"


@patch('select.poll')
@patch('socket.socket.recvfrom')
def test_probing(mock_recv, mock_poll):

    # read in the captured SOAP probe response
    curdir = os.path.dirname(__file__)
    with open(curdir + "/data/probe_response.xml", "rb") as resp:
        canned = resp.read()


    def mock_poll_fd(*args, **kwargs):
        "set correct poll.poll() response"
        sck = args[0] # poll.register is called with socket as a parameter
        if sck.proto == socket.IPPROTO_UDP:
            fn = sck.fileno()
            # mock up a claim that the registered fd has data
            mock_poll.return_value.poll.return_value = [(fn, select.POLLIN)]

    mock_poll.return_value.register.side_effect = mock_poll_fd
    mock_poll.return_value.poll.return_value = [(5, select.POLLIN)]
    mock_recv.return_value = (canned, DISCOVER_IP)

    wsd = WSDiscovery()
    wsd.start()
    services = wsd.searchServices()
    wsd.stop()
    s = services[0]
    assert s.getXAddrs()[0] == 'http://%s:80/onvif/device_service' % DISCOVER_IP
    assert len(s.getScopes()) == 4
