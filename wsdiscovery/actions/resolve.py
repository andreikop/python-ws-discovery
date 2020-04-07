"Serialize & parse WS-Discovery Resolve SOAP messages"

import uuid

from ..namespaces import NS_ADDRESSING, NS_DISCOVERY, NS_ACTION_RESOLVE, NS_ADDRESS_ALL
from ..envelope import SoapEnvelope
from ..util import createSkelSoapMessage, getBodyEl, getHeaderEl, addElementWithText, \
                   addEPR, addTypes, addScopes, getDocAsString, getScopes


def constructResolve(epr):
    "construct an envelope that represents a ``Resolve`` message"

    env = SoapEnvelope()
    env.setAction(NS_ACTION_RESOLVE)
    env.setTo(NS_ADDRESS_ALL)
    env.setMessageId(uuid.uuid4().urn)
    env.setEPR(epr)
    return env


def createResolveMessage(env):
    "serialize a SOAP envelope object into a string"

    doc = createSkelSoapMessage(NS_ACTION_RESOLVE)

    bodyEl = getBodyEl(doc)
    headerEl = getHeaderEl(doc)

    addElementWithText(doc, headerEl, "a:MessageID", NS_ADDRESSING, env.getMessageId())
    addElementWithText(doc, headerEl, "a:To", NS_ADDRESSING, env.getTo())

    if len(env.getReplyTo()) > 0:
        addElementWithText(doc, headerEl, "a:ReplyTo", NS_ADDRESSING, env.getReplyTo())

    resolveEl = doc.createElementNS(NS_DISCOVERY, "d:Resolve")
    addEPR(doc, resolveEl, env.getEPR())
    bodyEl.appendChild(resolveEl)

    return getDocAsString(doc)


def parseResolveMessage(dom):
    "parse a XML message into a SOAP envelope object"

    env = SoapEnvelope()
    env.setAction(NS_ACTION_RESOLVE)

    env.setMessageId(dom.getElementsByTagNameNS(NS_ADDRESSING, "MessageID")[0].firstChild.data.strip())

    replyToNodes = dom.getElementsByTagNameNS(NS_ADDRESSING, "ReplyTo")
    if len(replyToNodes) > 0:
        env.setReplyTo(replyToNodes[0].firstChild.data.strip())

    env.setTo(dom.getElementsByTagNameNS(NS_ADDRESSING, "To")[0].firstChild.data.strip())
    env.setEPR(dom.getElementsByTagNameNS(NS_ADDRESSING, "Address")[0].firstChild.data.strip())

    return env


