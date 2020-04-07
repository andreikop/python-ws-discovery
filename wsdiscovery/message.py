"""Functions to serialize and deserialize messages between SOAP envelope & string representations"""

import io
from .namespaces import NS_ADDRESSING, NS_SOAPENV
from .actions import *
from xml.dom import minidom


def createSOAPMessage(env):
    "serialize SOAP envelopes into XML strings"

    if env.getAction() == NS_ACTION_PROBE:
        return createProbeMessage(env)
    if env.getAction() == NS_ACTION_PROBE_MATCH:
        return createProbeMatchMessage(env)
    if env.getAction() == NS_ACTION_RESOLVE:
        return createResolveMessage(env)
    if env.getAction() == NS_ACTION_RESOLVE_MATCH:
        return createResolveMatchMessage(env)
    if env.getAction() == NS_ACTION_HELLO:
        return createHelloMessage(env)
    if env.getAction() == NS_ACTION_BYE:
        return createByeMessage(env)


def parseSOAPMessage(data, ipAddr):
    "deserialize XML message strings into SOAP envelope objects"

    try:
        dom = minidom.parseString(data)
    except Exception:
        #print('Failed to parse message from %s\n"%s": %s' % (ipAddr, data, ex), file=sys.stderr)
        return None

    if dom.getElementsByTagNameNS(NS_SOAPENV, "Fault"):
        #print('Fault received from %s:' % (ipAddr, data), file=sys.stderr)
        return None

    soapAction = dom.getElementsByTagNameNS(NS_ADDRESSING, "Action")[0].firstChild.data.strip()
    if soapAction == NS_ACTION_PROBE:
        return parseProbeMessage(dom)
    elif soapAction == NS_ACTION_PROBE_MATCH:
        return parseProbeMatchMessage(dom)
    elif soapAction == NS_ACTION_RESOLVE:
        return parseResolveMessage(dom)
    elif soapAction == NS_ACTION_RESOLVE_MATCH:
        return parseResolveMatchMessage(dom)
    elif soapAction == NS_ACTION_BYE:
        return parseByeMessage(dom)
    elif soapAction == NS_ACTION_HELLO:
        return parseHelloMessage(dom)
