import select
import socket
from .fixtures import wsd, probe_response
from mock import patch


@patch('select.poll')
@patch('socket.socket.recvfrom')
def test_probing(mock_recv, mock_poll, wsd, probe_response):

    def mock_poll_fd(*args, **kwargs):
        "set correct poll.poll() response"
        sck = args[0] # poll.register is called with socket as a parameter
        if sck.proto == socket.IPPROTO_UDP:
            fn = sck.fileno()
            # mock up a claim that the registered fd has data
            mock_poll.return_value.poll.return_value = [(fn, select.POLLIN)]

    mock_poll.return_value.register.side_effect = mock_poll_fd
    mock_recv.return_value = probe_response

    found = wsd.searchServices()
    assert len(found) == 1
    assert probe_response[1] in found[0].getXAddrs()[0]
    assert len(found[0].getScopes()) == 4
