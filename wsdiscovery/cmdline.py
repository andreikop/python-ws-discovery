import sys
import logging
from contextlib import contextmanager
from urllib.parse import urlparse
import click
from wsdiscovery.discovery import ThreadedWSDiscovery as WSDiscovery
from wsdiscovery.publishing import ThreadedWSPublishing as WSPublishing
from wsdiscovery.scope import Scope
from wsdiscovery.qname import QName

logging.basicConfig()

DEFAULT_LOGLEVEL = logging.INFO

@contextmanager
def discovery(capture=None):
    wsd = WSDiscovery(capture=capture)
    wsd.start()
    yield wsd
    wsd.stop()

@contextmanager
def publishing(capture=None):
    wsd = WSPublishing(capture=capture)
    wsd.start()
    yield wsd
    wsd.stop()


def get_logger(name, loglevel):
    if loglevel:
        level = getattr(logging, loglevel, None)
        if not level:
            print("Invalid log level '%s'" % loglevel)
            sys.exit()
    else:
        level = DEFAULT_LOGLEVEL

    logger = logging.getLogger(name)
    logger.setLevel(level)


@click.command()
@click.option('--scope', '-s', help='Full scope URI, eg. onvif://www.onvif.org/Model/')
@click.option('--address', '-a', help='Service address')
@click.option('--port', '-p', type=int, help='Service port')
@click.option('--loglevel', '-l',  help='Log level; one of INFO, DEBUG, WARNING, ERROR')
@click.option('--capture', '-c', nargs=1, type=click.File('w'), help='Capture messages to a file')
def discover(scope, address, port, loglevel, capture):
    "Discover services using WS-Discovery"

    logger = get_logger("ws-discovery", loglevel)

    with discovery(capture) as wsd:
        scopes = [Scope(scope)] if scope else []
        svcs = wsd.searchServices(scopes=scopes, address=address, port=port)
        print("\nDiscovered:\n")
        for service in svcs:
            url = urlparse(service.getXAddrs()[0])
            print(" address: %s" % url.netloc)
            print("  - %s\n" % "\n  - ".join([str(s) for s in service.getScopes()]))


@click.command()
@click.option('--scope', '-s', help='Full scope URI, eg. onvif://www.onvif.org/Model/')
@click.option('--typename', '-t', help='Qualified type name, eg. https://myservicesns:myservice_type')
@click.option('--address', '-a', help='Service IP address')
@click.option('--port', '-p', type=int, help='Service port')
@click.option('--loglevel', '-l',  help='Log level; one of INFO, DEBUG, WARNING, ERROR')
@click.option('--capture', '-c', nargs=1, type=click.File('w'), help='Capture messages to a file')
def publish(scope, typename, address, port, loglevel, capture):
    "Publish services using WS-Discovery"

    logger = get_logger("ws-publishing", loglevel)

    with publishing(capture) as wsp:
        scopes = [Scope(scope)] if scope else []

        try:
            proto, ns, name = typename.split(':')
        except:
            types = []
        else:
            ns = ns[2:]
            types = [QName(proto, ns)]

        xAddrs = ["%s:%i" % (address, port)] if address else ['127.0.0.1']
        svc = wsp.publishService(types, scopes, xAddrs)

