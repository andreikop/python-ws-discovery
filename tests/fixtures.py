import os
import pytest
from wsdiscovery import WSDiscovery


@pytest.fixture
def wsd():
    "provide the discovery client"
    client = WSDiscovery()
    client.start()
    yield client
    client.stop()


@pytest.fixture
def probe_response():
    "provide a captured SOAP probe response"

    DISCOVER_IP = "192.168.1.104"

    curdir = os.path.dirname(__file__)
    with open(curdir + "/data/probe_response.xml", "rb") as resp:
        canned = resp.read()
    return (canned, DISCOVER_IP)
