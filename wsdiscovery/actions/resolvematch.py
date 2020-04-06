"Serialize & parse WS-Discovery Resolve Match SOAP messages"

import uuid

from ..namespaces import NS_ADDRESSING, NS_DISCOVERY, NS_ACTION_RESOLVE_MATCH, NS_ADDRESS_UNKNOWN
from ..envelope import SoapEnvelope
from ..util import createSkelSoapMessage, getBodyEl, getHeaderEl, addElementWithText, \
                   addTypes, getTypes, addScopes, getDocAsString, getScopes, addEPR, \
                   addXAddrs, getXAddrs, _parseAppSequence
                   
from .probematch import ProbeResolveMatch


def constructResolveMatch(service, relatesTo):
    "construct an envelope that represents a ``Resolve Match`` message"

    service.incrementMessageNumber()

    env = SoapEnvelope()
    env.setAction(NS_ACTION_RESOLVE_MATCH)
    env.setTo(NS_ADDRESS_UNKNOWN)
    env.setMessageId(uuid.uuid4().urn)
    env.setInstanceId(str(service.getInstanceId()))
    env.setMessageNumber(str(service.getMessageNumber()))
    env.setRelatesTo(relatesTo)

    prb = ProbeResolveMatch(service.getEPR(), service.getTypes(), service.getScopes(), \
                            service.getXAddrs(), str(service.getMetadataVersion()))
    env.getProbeResolveMatches().append(prb)
    return env


def createResolveMatchMessage(env):
    "serialize a SOAP envelope object into a string"

    doc = createSkelSoapMessage(NS_ACTION_RESOLVE_MATCH)

    bodyEl = getBodyEl(doc)
    headerEl = getHeaderEl(doc)

    addElementWithText(doc, headerEl, "a:MessageID", NS_ADDRESSING, env.getMessageId())
    addElementWithText(doc, headerEl, "a:RelatesTo", NS_ADDRESSING, env.getRelatesTo())
    addElementWithText(doc, headerEl, "a:To", NS_ADDRESSING, env.getTo())

    appSeqEl = doc.createElementNS(NS_DISCOVERY, "d:AppSequence")
    appSeqEl.setAttribute("InstanceId", env.getInstanceId())
    appSeqEl.setAttribute("MessageNumber", env.getMessageNumber())
    headerEl.appendChild(appSeqEl)

    resolveMatchesEl = doc.createElementNS(NS_DISCOVERY, "d:ResolveMatches")
    if len(env.getProbeResolveMatches()) > 0:
        resolveMatch = env.getProbeResolveMatches()[0]
        resolveMatchEl = doc.createElementNS(NS_DISCOVERY, "d:ResolveMatch")
        addEPR(doc, resolveMatchEl, resolveMatch.getEPR())
        addTypes(doc, resolveMatchEl, resolveMatch.getTypes())
        addScopes(doc, resolveMatchEl, resolveMatch.getScopes())
        addXAddrs(doc, resolveMatchEl, resolveMatch.getXAddrs())
        addElementWithText(doc, resolveMatchEl, "d:MetadataVersion", NS_DISCOVERY, resolveMatch.getMetadataVersion())

        resolveMatchesEl.appendChild(resolveMatchEl)

    bodyEl.appendChild(resolveMatchesEl)

    return getDocAsString(doc)


def parseResolveMatchMessage(dom):
    "parse a XML message into a SOAP envelope object"

    env = SoapEnvelope()
    env.setAction(NS_ACTION_RESOLVE_MATCH)

    env.setMessageId(dom.getElementsByTagNameNS(NS_ADDRESSING, "MessageID")[0].firstChild.data.strip())
    env.setRelatesTo(dom.getElementsByTagNameNS(NS_ADDRESSING, "RelatesTo")[0].firstChild.data.strip())
    env.setTo(dom.getElementsByTagNameNS(NS_ADDRESSING, "To")[0].firstChild.data.strip())

    _parseAppSequence(dom, env)

    nodes = dom.getElementsByTagNameNS(NS_DISCOVERY, "ResolveMatch")
    if len(nodes) > 0:
        node = nodes[0]
        epr = node.getElementsByTagNameNS(NS_ADDRESSING, "Address")[0].firstChild.data.strip()

        typeNodes = node.getElementsByTagNameNS(NS_DISCOVERY, "Types")
        types = []
        if len(typeNodes) > 0:
            types = getTypes(typeNodes[0])

        scopeNodes = node.getElementsByTagNameNS(NS_DISCOVERY, "Scopes")
        scopes = []
        if len(scopeNodes) > 0:
            scopes = getScopes(scopeNodes[0])

        xAddrs = getXAddrs(node.getElementsByTagNameNS(NS_DISCOVERY, "XAddrs")[0])
        mdv = node.getElementsByTagNameNS(NS_DISCOVERY, "MetadataVersion")[0].firstChild.data.strip()
        env.getProbeResolveMatches().append(ProbeResolveMatch(epr, types, scopes, xAddrs, mdv))

    return env





