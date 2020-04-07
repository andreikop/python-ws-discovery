"Serialize & parse WS-Discovery Hello SOAP messages"

import uuid
from ..namespaces import NS_ADDRESSING, NS_DISCOVERY, NS_ACTION_HELLO, NS_ADDRESS_ALL
from ..envelope import SoapEnvelope
from ..util import createSkelSoapMessage, getBodyEl, getHeaderEl, addElementWithText, \
                   addTypes, addScopes, getDocAsString, getScopes, getQNameFromValue, \
                   addEPR, addXAddrs, _parseAppSequence, getTypes, getXAddrs


def constructHello(service):
    "construct an envelope that represents a ``Hello`` message"

    service.incrementMessageNumber()

    env = SoapEnvelope()
    env.setAction(NS_ACTION_HELLO)
    env.setTo(NS_ADDRESS_ALL)
    env.setMessageId(uuid.uuid4().urn)
    env.setInstanceId(str(service.getInstanceId()))
    env.setMessageNumber(str(service.getMessageNumber()))
    env.setTypes(service.getTypes())
    env.setScopes(service.getScopes())
    env.setXAddrs(service.getXAddrs())
    env.setEPR(service.getEPR())
    return env


def createHelloMessage(env):
    "serialize a SOAP envelope object into a string"
    doc = createSkelSoapMessage(NS_ACTION_HELLO)

    bodyEl = getBodyEl(doc)
    headerEl = getHeaderEl(doc)

    addElementWithText(doc, headerEl, "a:MessageID", NS_ADDRESSING, env.getMessageId())

    if len(env.getRelatesTo()) > 0:
        addElementWithText(doc, headerEl, "a:RelatesTo", NS_ADDRESSING, env.getRelatesTo())
        relatesToEl = headerEl.getElementsByTagNameNS(NS_ADDRESSING, "RelatesTo")[0]
        relatesToEl.setAttribute("RelationshipType", "d:Suppression")

    addElementWithText(doc, headerEl, "a:To", NS_ADDRESSING, env.getTo())

    appSeqEl = doc.createElementNS(NS_DISCOVERY, "d:AppSequence")
    appSeqEl.setAttribute("InstanceId", env.getInstanceId())
    appSeqEl.setAttribute("MessageNumber", env.getMessageNumber())
    headerEl.appendChild(appSeqEl)

    helloEl = doc.createElementNS(NS_DISCOVERY, "d:Hello")
    addEPR(doc, helloEl, env.getEPR())
    addTypes(doc, helloEl, env.getTypes())
    addScopes(doc, helloEl, env.getScopes())
    addXAddrs(doc, helloEl, env.getXAddrs())
    addElementWithText(doc, helloEl, "d:MetadataVersion", NS_DISCOVERY, env.getMetadataVersion())

    bodyEl.appendChild(helloEl)

    return getDocAsString(doc)


def parseHelloMessage(dom):
    "parse a XML message into a SOAP envelope object"
    env = SoapEnvelope()
    env.setAction(NS_ACTION_HELLO)

    env.setMessageId(dom.getElementsByTagNameNS(NS_ADDRESSING, "MessageID")[0].firstChild.data.strip())
    env.setTo(dom.getElementsByTagNameNS(NS_ADDRESSING, "To")[0].firstChild.data.strip())

    _parseAppSequence(dom, env)

    relatesToNodes = dom.getElementsByTagNameNS(NS_ADDRESSING, "RelatesTo")
    if len(relatesToNodes) > 0:
        env.setRelatesTo(relatesToNodes[0].firstChild.data.strip())
        env.setRelationshipType(getQNameFromValue( \
            relatesToNodes[0].getAttribute("RelationshipType"), relatesToNodes[0]))

    env.setEPR(dom.getElementsByTagNameNS(NS_ADDRESSING, "Address")[0].firstChild.data.strip())

    typeNodes = dom.getElementsByTagNameNS(NS_DISCOVERY, "Types")
    if len(typeNodes) > 0:
        env.setTypes(getTypes(typeNodes[0]))

    scopeNodes = dom.getElementsByTagNameNS(NS_DISCOVERY, "Scopes")
    if len(scopeNodes) > 0:
        env.setScopes(getScopes(scopeNodes[0]))

    xNodes = dom.getElementsByTagNameNS(NS_DISCOVERY, "XAddrs")
    if len(xNodes) > 0:
        env.setXAddrs(getXAddrs(xNodes[0]))

    env.setMetadataVersion(dom.getElementsByTagNameNS(NS_DISCOVERY, "MetadataVersion")[0].firstChild.data.strip())

    return env
