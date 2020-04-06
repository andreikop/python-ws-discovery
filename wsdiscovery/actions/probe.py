"Serialize & parse WS-Discovery Probe SOAP messages"

import uuid
from xml.dom import minidom

from ..namespaces import NS_ADDRESSING, NS_DISCOVERY, NS_ACTION_PROBE, NS_ADDRESS_ALL
from ..envelope import SoapEnvelope
from ..util import createSkelSoapMessage, getBodyEl, getHeaderEl, addElementWithText, \
                   addTypes, getTypes, addScopes, getDocAsString, getScopes


def constructProbe(types, scopes):
    "construct an envelope that represents a ``Probe`` message"

    env = SoapEnvelope()
    env.setAction(NS_ACTION_PROBE)
    env.setTo(NS_ADDRESS_ALL)
    env.setMessageId(uuid.uuid4().urn)
    env.setTypes(types)
    env.setScopes(scopes)
    return env


def createProbeMessage(env):
    "serialize a SOAP envelope object into a string"

    doc = createSkelSoapMessage(NS_ACTION_PROBE)

    bodyEl = getBodyEl(doc)
    headerEl = getHeaderEl(doc)

    addElementWithText(doc, headerEl, "a:MessageID", NS_ADDRESSING, env.getMessageId())
    addElementWithText(doc, headerEl, "a:To", NS_ADDRESSING, env.getTo())

    if len(env.getReplyTo()) > 0:
        addElementWithText(doc, headerEl, "a:ReplyTo", NS_ADDRESSING, env.getReplyTo())

    probeEl = doc.createElementNS(NS_DISCOVERY, "d:Probe")
    bodyEl.appendChild(probeEl)

    addTypes(doc, probeEl, env.getTypes())
    addScopes(doc, probeEl, env.getScopes())

    return getDocAsString(doc)


def parseProbeMessage(dom):
    "parse a XML message into a SOAP envelope object"

    env = SoapEnvelope()
    env.setAction(NS_ACTION_PROBE)
    env.setMessageId(dom.getElementsByTagNameNS(NS_ADDRESSING, "MessageID")[0].firstChild.data.strip())

    replyToNodes = dom.getElementsByTagNameNS(NS_ADDRESSING, "ReplyTo")
    if len(replyToNodes) > 0 and \
       isinstance(replyToNodes[0].firstChild, minidom.Text):
        env.setReplyTo(replyToNodes[0].firstChild.data.strip())

    env.setTo(dom.getElementsByTagNameNS(NS_ADDRESSING, "To")[0].firstChild.data.strip())

    typeNodes = dom.getElementsByTagNameNS(NS_DISCOVERY, "Types")
    if len(typeNodes) > 0:
        env.getTypes().extend(getTypes(typeNodes[0]))

    scopeNodes = dom.getElementsByTagNameNS(NS_DISCOVERY, "Scopes")
    if len(scopeNodes) > 0:
        env.getScopes().extend(getScopes(scopeNodes[0]))

    return env




