import sys
import logging
from contextlib import contextmanager
from urllib.parse import urlparse
import click

from wsdiscovery.discovery import ThreadedWSDiscovery as WSDiscovery
from wsdiscovery.publishing import ThreadedWSPublishing as WSPublishing
from wsdiscovery.scope import Scope
from wsdiscovery.qname import QName
from wsdiscovery.discovery import DEFAULT_DISCOVERY_TIMEOUT
from wsdiscovery.udp import UNICAST_UDP_REPEAT, MULTICAST_UDP_REPEAT

DEFAULT_LOGLEVEL = "INFO"

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@contextmanager
def discovery(capture=None, unicast_num=UNICAST_UDP_REPEAT,
              multicast_num=MULTICAST_UDP_REPEAT, relates_to=False):
    wsd = WSDiscovery(capture=capture, unicast_num=unicast_num,
                      multicast_num=multicast_num, relates_to=relates_to)
    wsd.start()
    yield wsd
    wsd.stop()

@contextmanager
def publishing(capture=None):
    wsd = WSPublishing(capture=capture)
    wsd.start()
    yield wsd
    wsd.stop()


def setup_logger(name, loglevel):
    level = getattr(logging, loglevel, None)
    if not level:
        print("Invalid log level '%s'" % loglevel)
        sys.exit()

    logging.basicConfig(level=level)
    return logging.getLogger(name)


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('--scope', '-s', help='Probe scope URI, e.g. onvif://www.onvif.org/Model/')
@click.option('--type', '-y', 'ptype', nargs=3, type=(str, str, str), multiple=True,
              help='Probe type in this order: NS_URI NS_PREFIX LOCAL_NAME,'
                   ' e.g. http://www.onvif.org/ver10/network/wsdl dp0 NetworkVideoTransmitter'
                   ' -- this option can be specified multiple times')
@click.option('--address', '-a', help='Service address')
@click.option('--port', '-p', type=int, help='Service port')
@click.option('--loglevel', '-l',  default=DEFAULT_LOGLEVEL, show_default=True,
              type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
              help='Log level')
@click.option('--capture', '-c', nargs=1, type=click.File('w'), help='Capture messages to a file')
@click.option('--timeout', '-t', default=DEFAULT_DISCOVERY_TIMEOUT, show_default=True,
              type=int, help='Discovery timeout in seconds')
@click.option('--unicast-num', '-un', type=int, default=UNICAST_UDP_REPEAT,
              show_default=True, help='Number of Unicast messages to send')
@click.option('--multicast-num', '-mn', type=int, default=MULTICAST_UDP_REPEAT,
              show_default=True, help='Number of Multicast messages to send')
@click.option('--relates-to', '-rt', is_flag=True,
              help='Also use RelatesTo tag to recognize incoming messages.')
def discover(scope, ptype, address, port, loglevel, capture, timeout,
             unicast_num, multicast_num, relates_to):
    "Discover services using WS-Discovery"

    logger = setup_logger("ws-discovery", loglevel)

    probe_types = []
    for type_tuple in ptype:
        probe_types.append(QName(type_tuple[0], type_tuple[2], type_tuple[1]))
    if len(probe_types) == 0:
        probe_types = None

    with discovery(capture, unicast_num, multicast_num, relates_to) as wsd:
        scopes = [Scope(scope)] if scope else []
        svcs = wsd.searchServices(types=probe_types, scopes=scopes,
                                  address=address, port=port, timeout=timeout)
        print("\nDiscovered:\n")
        for service in svcs:
            url = urlparse(service.getXAddrs()[0])
            print(" address: %s" % url.netloc)
            print("  - %s\n" % "\n  - ".join([str(s) for s in service.getScopes()]))


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('--scope', '-s', help='Full scope URI, eg. onvif://www.onvif.org/Model/')
@click.option('--typename', '-t', help='Qualified type name, eg. https://myservicesns:myservice_type')
@click.option('--address', '-a', help='Service IP address')
@click.option('--port', '-p', type=int, help='Service port')
@click.option('--loglevel', '-l',  default=DEFAULT_LOGLEVEL, show_default=True,
              type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
              help='Log level')
@click.option('--capture', '-c', nargs=1, type=click.File('w'), help='Capture messages to a file')
@click.option('--unicast-num', '-un', type=int, default=UNICAST_UDP_REPEAT,
              show_default=True, help='Number of Unicast messages to send')
@click.option('--multicast-num', '-mn', type=int, default=MULTICAST_UDP_REPEAT,
              show_default=True, help='Number of Multicast messages to send')
def publish(scope, typename, address, port, loglevel, capture, unicast_num,
            multicast_num):
    "Publish services using WS-Discovery"

    logger = setup_logger("ws-publishing", loglevel)

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
