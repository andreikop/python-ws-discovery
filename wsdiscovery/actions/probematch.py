"Serialize & parse WS-Discovery Probe Match SOAP messages"

import uuid
import random
import time

from ..namespaces import NS_ADDRESSING, NS_DISCOVERY, NS_ACTION_PROBE_MATCH, NS_ADDRESS_UNKNOWN
from ..envelope import SoapEnvelope
from ..util import createSkelSoapMessage, getBodyEl, getHeaderEl, addElementWithText, \
                   addTypes, addScopes, getDocAsString, getScopes, _parseAppSequence, \
                   addEPR, getXAddrs, addXAddrs, getTypes, _generateInstanceId


def constructProbeMatch(services, relatesTo):
    "construct an envelope that represents a ``Probe Match`` message"

    env = SoapEnvelope()
    env.setAction(NS_ACTION_PROBE_MATCH)
    env.setTo(NS_ADDRESS_UNKNOWN)
    env.setMessageId(uuid.uuid4().urn)
    random.seed((int)(time.time() * 1000000))
    env.setInstanceId(_generateInstanceId())
    env.setMessageNumber("1")
    env.setRelatesTo(relatesTo)

    prbs =  env.getProbeResolveMatches()
    for srv in services:
        prb = ProbeResolveMatch(srv.getEPR(), srv.getTypes(), srv.getScopes(), \
                                srv.getXAddrs(), str(srv.getMetadataVersion()))
        prbs.append(prb)
    return env


def createProbeMatchMessage(env):
    "serialize a SOAP envelope object into a string"

    doc = createSkelSoapMessage(NS_ACTION_PROBE_MATCH)

    bodyEl = getBodyEl(doc)
    headerEl = getHeaderEl(doc)

    addElementWithText(doc, headerEl, "a:MessageID", NS_ADDRESSING, env.getMessageId())
    addElementWithText(doc, headerEl, "a:RelatesTo", NS_ADDRESSING, env.getRelatesTo())
    addElementWithText(doc, headerEl, "a:To", NS_ADDRESSING, env.getTo())

    appSeqEl = doc.createElementNS(NS_DISCOVERY, "d:AppSequence")
    appSeqEl.setAttribute("InstanceId", env.getInstanceId())
    appSeqEl.setAttribute("MessageNumber", env.getMessageNumber())
    headerEl.appendChild(appSeqEl)

    probeMatchesEl = doc.createElementNS(NS_DISCOVERY, "d:ProbeMatches")
    probeMatches = env.getProbeResolveMatches()
    for probeMatch in probeMatches:
        probeMatchEl = doc.createElementNS(NS_DISCOVERY, "d:ProbeMatch")
        addEPR(doc, probeMatchEl, probeMatch.getEPR())
        addTypes(doc, probeMatchEl, probeMatch.getTypes())
        addScopes(doc, probeMatchEl, probeMatch.getScopes())
        addXAddrs(doc, probeMatchEl, probeMatch.getXAddrs())
        addElementWithText(doc, probeMatchEl, "d:MetadataVersion", NS_DISCOVERY, probeMatch.getMetadataVersion())
        probeMatchesEl.appendChild(probeMatchEl)


    bodyEl.appendChild(probeMatchesEl)

    return getDocAsString(doc)


def parseProbeMatchMessage(dom):
    "parse a XML message into a SOAP envelope object"

    env = SoapEnvelope()
    env.setAction(NS_ACTION_PROBE_MATCH)

    env.setMessageId(dom.getElementsByTagNameNS(NS_ADDRESSING, "MessageID")[0].firstChild.data.strip())
    env.setRelatesTo(dom.getElementsByTagNameNS(NS_ADDRESSING, "RelatesTo")[0].firstChild.data.strip())
    # Even though To is required in WS-Discovery, some devices omit it
    elem = dom.getElementsByTagNameNS(NS_ADDRESSING, "To").item(0)
    if elem:
        env.setTo(elem.firstChild.data.strip())

    _parseAppSequence(dom, env)

    pmNodes = dom.getElementsByTagNameNS(NS_DISCOVERY, "ProbeMatch")
    for node in pmNodes:
        epr = node.getElementsByTagNameNS(NS_ADDRESSING, "Address")[0].firstChild.data.strip()

        types = []
        typeNodes = node.getElementsByTagNameNS(NS_DISCOVERY, "Types")
        if len(typeNodes) > 0:
            types = getTypes(typeNodes[0])

        scopes = []
        scopeNodes = node.getElementsByTagNameNS(NS_DISCOVERY, "Scopes")
        if len(scopeNodes) > 0:
            scopes = getScopes(scopeNodes[0])

        xAddrs = []
        xAddrNodes = node.getElementsByTagNameNS(NS_DISCOVERY, "XAddrs")
        if len(xAddrNodes) > 0:
            xAddrs = getXAddrs(xAddrNodes[0])

        mdv = node.getElementsByTagNameNS(NS_DISCOVERY, "MetadataVersion")[0].firstChild.data.strip()
        env.getProbeResolveMatches().append(ProbeResolveMatch(epr, types, scopes, xAddrs, mdv))

    return env



class ProbeResolveMatch:

    def __init__(self, epr, types, scopes, xAddrs, metadataVersion):
        self._epr = epr
        self._types = types
        self._scopes = scopes
        self._xAddrs = xAddrs
        self._metadataVersion = metadataVersion

    def getEPR(self):
        return self._epr

    def getTypes(self):
        return self._types

    def getScopes(self):
        return self._scopes

    def getXAddrs(self):
        return self._xAddrs

    def getMetadataVersion(self):
        return self._metadataVersion

    def __repr__(self):
        return "EPR: %s\nTypes: %s\nScopes: %s\nXAddrs: %s\nMetadata Version: %s" % \
            (self.getEPR(), self.getTypes(), self.getScopes(),
             self.getXAddrs(), self.getMetadataVersion())



