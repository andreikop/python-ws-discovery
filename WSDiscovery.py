#!/usr/bin/env python

import urllib
from xml.dom import minidom
import StringIO
import random
import string
import socket
import struct
import time
import uuid
import threading
import thread
import sys
import select
import netifaces


BUFFER_SIZE = 0xffff
APP_MAX_DELAY = 500 # miliseconds
DP_MAX_TIMEOUT = 5000 # 5 seconds

_NETWORK_ADDRESSES_CHECK_TIMEOUT = 5

MULTICAST_PORT = 3702
MULTICAST_IPV4_ADDRESS = "239.255.255.250"

UNICAST_UDP_REPEAT=2
UNICAST_UDP_MIN_DELAY=50
UNICAST_UDP_MAX_DELAY=250
UNICAST_UDP_UPPER_DELAY=500

MULTICAST_UDP_REPEAT=4
MULTICAST_UDP_MIN_DELAY=50
MULTICAST_UDP_MAX_DELAY=250
MULTICAST_UDP_UPPER_DELAY=500

NS_A = "http://schemas.xmlsoap.org/ws/2004/08/addressing"
NS_D = "http://schemas.xmlsoap.org/ws/2005/04/discovery"
NS_S = "http://www.w3.org/2003/05/soap-envelope"

ACTION_HELLO = "http://schemas.xmlsoap.org/ws/2005/04/discovery/Hello"
ACTION_BYE = "http://schemas.xmlsoap.org/ws/2005/04/discovery/Bye"
ACTION_PROBE = "http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe"
ACTION_PROBE_MATCH = "http://schemas.xmlsoap.org/ws/2005/04/discovery/ProbeMatches"
ACTION_RESOLVE = "http://schemas.xmlsoap.org/ws/2005/04/discovery/Resolve"
ACTION_RESOLVE_MATCH = "http://schemas.xmlsoap.org/ws/2005/04/discovery/ResolveMatches"

ADDRESS_ALL = "urn:schemas-xmlsoap-org:ws:2005:04:discovery"
ADDRESS_UNKNOWN = "http://schemas.xmlsoap.org/ws/2004/08/addressing/role/anonymous"

MATCH_BY_LDAP = "http://schemas.xmlsoap.org/ws/2005/04/discovery/ldap"
MATCH_BY_URI = "http://schemas.xmlsoap.org/ws/2005/04/discovery/rfc2396"
MATCH_BY_UUID = "http://schemas.xmlsoap.org/ws/2005/04/discovery/uuid"
MATCH_BY_STRCMP = "http://schemas.xmlsoap.org/ws/2005/04/discovery/strcmp0"


def _getNetworkAddrs():
    result = []
    
    for if_name in netifaces.interfaces():
        iface_info = netifaces.ifaddresses(if_name)
        if netifaces.AF_INET in iface_info:
            for addrDict in iface_info[netifaces.AF_INET]:
                addr = addrDict['addr']
                if addr != '127.0.0.1':
                    result.append(addr)
    return result


def _generateInstanceId():
    return str(random.randint(1, 0xFFFFFFFF))


class _StopableDaemonThread(threading.Thread):
    """Stopable daemon thread.
    
    run() method shall exit, when self._quitEvent.wait() returned True
    """
    def __init__(self):
        self._quitEvent = threading.Event()
        super(_StopableDaemonThread, self).__init__()
        self.daemon = True
   
    def schedule_stop(self):
        """Schedule stopping the thread.
        Use join() to wait, until thread really has been stopped
        """
        self._quitEvent.set()


class URI:

    def __init__(self, uri):
        uri = urllib.unquote(uri)
        i1 = uri.find(":")
        i2 = uri.find("@")
        self._scheme = uri[:i1]
        if i2 != -1:
            self._authority = uri[i1 + 1: i2]
            self._path = uri[i2 + 1:]
        else:
            self._authority = ""
            self._path = uri[i1 + 1:]

    def getScheme(self):
        return self._scheme

    def getAuthority(self):
        return self._authority

    def getPath(self):
        return self._path

    def getPathExQueryFragment(self):
        i = self._path.find("?")
        path = self.getPath()
        if i != -1:
            return path[:self._path.find("?")]
        else:
            return path

class QName:

    def __init__(self, namespace, localname):        
        self._namespace = namespace
        self._localname = localname

    def getNamespace(self):
        return self._namespace

    def getLocalname(self):
        return self._localname

    def getFullname(self):
        return self.getNamespace() + ":" + self.getLocalname()

    def __repr__(self):
        return self.getFullname()
        

class Scope:

    def __init__(self, value, matchBy=None):
        self._matchBy = matchBy
        self._value = value

    def getMatchBy(self):
        return self._matchBy

    def getValue(self):
        return self._value

    def getQuotedValue(self):
        return self._value.replace(' ', '%20')
    
    def __repr__(self):
        if self.getMatchBy() == None or len(self.getMatchBy()) == 0:
            return self.getValue()
        else:
            return self.getMatchBy() + ":" + self.getValue()

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

class SoapEnvelope:

    def __init__(self):
        self._action = ""
        self._messageId = ""
        self._relatesTo = ""
        self._relationshipType = None
        self._to = ""
        self._replyTo = ""
        self._instanceId = ""
        self._sequenceId = ""
        self._messageNumber = ""
        self._epr = ""
        self._types = []
        self._scopes = []
        self._xAddrs = []
        self._metadataVersion = "1"
        self._probeResolveMatches = []

    def getAction(self):
        return self._action

    def setAction(self, action):
        self._action = action

    def getMessageId(self):
        return self._messageId

    def setMessageId(self, messageId):
        self._messageId = messageId

    def getRelatesTo(self):
        return self._relatesTo

    def setRelatesTo(self, relatesTo):
        self._relatesTo = relatesTo

    def getRelationshipType(self):
        return self._relationshipType

    def setRelationshipType(self, relationshipType):
        self._relationshipType = relationshipType

    def getTo(self):
        return self._to
    
    def setTo(self, to):
        self._to = to

    def getReplyTo(self):
        return self._replyTo
    
    def setReplyTo(self, replyTo):
        self._replyTo = replyTo

    def getInstanceId(self):
        return self._instanceId

    def setInstanceId(self, instanceId):
        self._instanceId = instanceId

    def getSequenceId(self):
        return self._sequenceId

    def setSequenceId(self, sequenceId):
        self._sequenceId = sequenceId
        
    def getEPR(self):
        return self._epr

    def setEPR(self, epr):
        self._epr = epr

    def getMessageNumber(self):
        return self._messageNumber

    def setMessageNumber(self, messageNumber):
        self._messageNumber = messageNumber

    def getTypes(self):
        return self._types

    def setTypes(self, types):
        self._types = types

    def getScopes(self):
        return self._scopes

    def setScopes(self, scopes):
        self._scopes = scopes

    def getXAddrs(self):
        return self._xAddrs

    def setXAddrs(self, xAddrs):
        self._xAddrs = xAddrs

    def getMetadataVersion(self):
        return self._metadataVersion

    def setMetadataVersion(self, metadataVersion):
        self._metadataVersion = metadataVersion

    def getProbeResolveMatches(self):
        return self._probeResolveMatches

    def setProbeResolveMatches(self, probeResolveMatches):
        self._probeResolveMatches = probeResolveMatches


def matchScope(src, target, matchBy):
    if matchBy == "" or matchBy == None or matchBy == MATCH_BY_LDAP or matchBy == MATCH_BY_URI or matchBy == MATCH_BY_UUID:
        src = URI(src)
        target = URI(target)
        if src.getScheme().lower() != target.getScheme().lower():
            return False
        if src.getAuthority().lower() != target.getAuthority().lower():
            return False
        srcPath = src.getPathExQueryFragment()
        targetPath = target.getPathExQueryFragment()
        if srcPath == targetPath:
            return True
        elif targetPath.startswith(srcPath):
            n = len(srcPath)
            if targetPath[n - 1] == srcPath[n - 1] == '/':
                return True
            if targetPath[n] == '/':
                return True
            return False
        else:
            return False
    elif matchBy == MATCH_BY_STRCMP:
        return src == target
    else:
        return False

def matchType(type1, type2):
    return type1.getFullname() == type2.getFullname()

def getNamespaceValue(node, prefix):
    while node != None:
        if node.nodeType == minidom.Node.ELEMENT_NODE:
            attr = node.getAttributeNode("xmlns:" + prefix)
            if attr != None:
                return attr.nodeValue
        node = node.parentNode
    return ""

def getDefaultNamespace(node):
    while node != None:
        if node.nodeType == minidom.Node.ELEMENT_NODE:
            attr = node.getAttributeNode("xmlns")
            if attr != None:
                return attr.nodeValue
        node = node.parentNode
    return ""

def getQNameFromValue(value, node):
    vals = value.split(":")
    ns = ""
    if len(vals) == 1:
        localName = vals[0]
        ns = getDefaultNamespace(node)
    else:
        localName = vals[1]
        ns = getNamespaceValue(node, vals[0])              
    return QName(ns, localName)

def _parseSpaceSeparatedList(node):
    if node.childNodes:
        return [item.replace('%20', ' ') \
            for item in node.childNodes[0].data.split()]
    else:
        return []

def getTypes(typeNode):
    return [getQNameFromValue(item, typeNode) \
                for item in _parseSpaceSeparatedList(typeNode)]

def getScopes(scopeNode):
    matchBy = scopeNode.getAttribute("MatchBy")
    return [Scope(item, matchBy) \
                for item in _parseSpaceSeparatedList(scopeNode)]

def getXAddrs(xAddrsNode):
    return _parseSpaceSeparatedList(xAddrsNode)

def createSkelSoapMessage(soapAction):
    doc = minidom.Document()

    envEl = doc.createElementNS(NS_S, "s:Envelope")
    
    envEl.setAttribute("xmlns:a", NS_A)  # minidom does not insert this automatically
    envEl.setAttribute("xmlns:d", NS_D)
    envEl.setAttribute("xmlns:s", NS_S)
    
    doc.appendChild(envEl)

    headerEl = doc.createElementNS(NS_S, "s:Header")
    envEl.appendChild(headerEl)

    addElementWithText(doc, headerEl, "a:Action", NS_A, soapAction)

    bodyEl = doc.createElementNS(NS_S, "s:Body")
    envEl.appendChild(bodyEl)

    return doc

def addElementWithText(doc, parent, name, ns, value):
    el = doc.createElementNS(ns, name)
    text = doc.createTextNode(value)
    el.appendChild(text)
    parent.appendChild(el)

def getDocAsString(doc):
    outStr = ""
    stream = StringIO.StringIO(outStr)
    stream.write(doc.toprettyxml())
    return stream.getvalue()

def getBodyEl(doc):
    return doc.getElementsByTagNameNS(NS_S, "Body")[0]

def getHeaderEl(doc):
    return doc.getElementsByTagNameNS(NS_S, "Header")[0]

def getEnvEl(doc):
    return doc.getElementsByTagNameNS(NS_S, "Envelope")[0]

def getRandomStr():
    return "".join([random.choice(string.letters) for x in xrange(10)])

def addNSAttrToEl(el, ns, prefix):
    el.setAttribute("xmlns:" + prefix, ns)
    
def addTypes(doc, node, types):
    if types is not None and len(types) > 0:
        envEl = getEnvEl(doc)
        typeList = []
        prefixMap = {}
        for type in types:
            ns = type.getNamespace()
            localname = type.getLocalname()
            if prefixMap.get(ns) == None:
                prefix = getRandomStr()
                prefixMap[ns] = prefix
            else:
                prefix = prefixMap.get(ns)
            addNSAttrToEl(envEl, ns, prefix)
            typeList.append(prefix + ":" + localname)
        addElementWithText(doc, node, "d:Types", NS_D, " ".join(typeList))

def addScopes(doc, node, scopes):
    if scopes is not None and len(scopes) > 0:
        addElementWithText(doc, node, "d:Scopes", NS_D, " ".join([x.getQuotedValue() for x in scopes]))
        if scopes[0].getMatchBy() is not None and len(scopes[0].getMatchBy()) > 0:
            node.getElementsByTagNameNS(NS_D, "Scopes")[0].setAttribute("MatchBy", scopes[0].getMatchBy())

def addXAddrs(doc, node, xAddrs):
    if xAddrs is not len(xAddrs) > 0:
        addElementWithText(doc, node, "d:XAddrs", NS_D, " ".join([x for x in xAddrs]))

def addEPR(doc, node, epr):
    eprEl = doc.createElementNS(NS_A, "a:EndpointReference")
    addElementWithText(doc, eprEl, "a:Address", NS_A, epr)
    node.appendChild(eprEl)


def parseProbeMessage(dom):
    env = SoapEnvelope()
    env.setAction(ACTION_PROBE)
    env.setMessageId(dom.getElementsByTagNameNS(NS_A, "MessageID")[0].firstChild.data.strip())

    replyToNodes = dom.getElementsByTagNameNS(NS_A, "ReplyTo")
    if len(replyToNodes) > 0 and \
       isinstance(replyToNodes[0].firstChild, minidom.Text):
        env.setReplyTo(replyToNodes[0].firstChild.data.strip())

    env.setTo(dom.getElementsByTagNameNS(NS_A, "To")[0].firstChild.data.strip())

    typeNodes = dom.getElementsByTagNameNS(NS_D, "Types")
    if len(typeNodes) > 0:
        env.getTypes().extend(getTypes(typeNodes[0]))

    scopeNodes = dom.getElementsByTagNameNS(NS_D, "Scopes")
    if len(scopeNodes) > 0:
        env.getScopes().extend(getScopes(scopeNodes[0]))
    
    return env


def _parseAppSequence(dom, env):
    nodes = dom.getElementsByTagNameNS(NS_D, "AppSequence")
    if nodes:
        appSeqNode = nodes[0]
        env.setInstanceId(appSeqNode.getAttribute("InstanceId"))
        env.setSequenceId(appSeqNode.getAttribute("SequenceId"))
        env.setMessageNumber(appSeqNode.getAttribute("MessageNumber"))


def parseProbeMatchMessage(dom):
    env = SoapEnvelope()
    env.setAction(ACTION_PROBE_MATCH)

    env.setMessageId(dom.getElementsByTagNameNS(NS_A, "MessageID")[0].firstChild.data.strip())
    env.setRelatesTo(dom.getElementsByTagNameNS(NS_A, "RelatesTo")[0].firstChild.data.strip())
    env.setTo(dom.getElementsByTagNameNS(NS_A, "To")[0].firstChild.data.strip())

    _parseAppSequence(dom, env)

    pmNodes = dom.getElementsByTagNameNS(NS_D, "ProbeMatch")
    for node in pmNodes:
        epr = node.getElementsByTagNameNS(NS_A, "Address")[0].firstChild.data.strip()
        
        types = []
        typeNodes = node.getElementsByTagNameNS(NS_D, "Types")
        if len(typeNodes) > 0:
            types = getTypes(typeNodes[0])

        scopes = []
        scopeNodes = node.getElementsByTagNameNS(NS_D, "Scopes")
        if len(scopeNodes) > 0:
            scopes = getScopes(scopeNodes[0])
            
        xAddrs = []
        xAddrNodes = node.getElementsByTagNameNS(NS_D, "XAddrs")
        if len(xAddrNodes) > 0:
            xAddrs = getXAddrs(xAddrNodes[0])
        
        mdv = node.getElementsByTagNameNS(NS_D, "MetadataVersion")[0].firstChild.data.strip()
        env.getProbeResolveMatches().append(ProbeResolveMatch(epr, types, scopes, xAddrs, mdv))
    
    return env

def parseResolveMessage(dom):
    env = SoapEnvelope()
    env.setAction(ACTION_RESOLVE)

    env.setMessageId(dom.getElementsByTagNameNS(NS_A, "MessageID")[0].firstChild.data.strip())
    
    replyToNodes = dom.getElementsByTagNameNS(NS_A, "ReplyTo")
    if len(replyToNodes) > 0:
        env.setReplyTo(replyToNodes[0].firstChild.data.strip())

    env.setTo(dom.getElementsByTagNameNS(NS_A, "To")[0].firstChild.data.strip())
    env.setEPR(dom.getElementsByTagNameNS(NS_A, "Address")[0].firstChild.data.strip())

    return env

def parseResolveMatchMessage(dom):
    env = SoapEnvelope()
    env.setAction(ACTION_RESOLVE_MATCH)

    env.setMessageId(dom.getElementsByTagNameNS(NS_A, "MessageID")[0].firstChild.data.strip())
    env.setRelatesTo(dom.getElementsByTagNameNS(NS_A, "RelatesTo")[0].firstChild.data.strip())
    env.setTo(dom.getElementsByTagNameNS(NS_A, "To")[0].firstChild.data.strip())

    _parseAppSequence(dom, env)

    nodes = dom.getElementsByTagNameNS(NS_D, "ResolveMatch")
    if len(nodes) > 0:
        node = nodes[0]
        epr = node.getElementsByTagNameNS(NS_A, "Address")[0].firstChild.data.strip()

        typeNodes = node.getElementsByTagNameNS(NS_D, "Types")
        types = []
        if len(typeNodes) > 0:
            types = getTypes(typeNodes[0])

        scopeNodes = node.getElementsByTagNameNS(NS_D, "Scopes")
        scopes = []
        if len(scopeNodes) > 0:
            scopes = getScopes(scopeNodes[0])
                    
        xAddrs = getXAddrs(node.getElementsByTagNameNS(NS_D, "XAddrs")[0])
        mdv = node.getElementsByTagNameNS(NS_D, "MetadataVersion")[0].firstChild.data.strip()
        env.getProbeResolveMatches().append(ProbeResolveMatch(epr, types, scopes, xAddrs, mdv))
    
    return env

def parseHelloMessage(dom):
    env = SoapEnvelope()
    env.setAction(ACTION_HELLO)

    env.setMessageId(dom.getElementsByTagNameNS(NS_A, "MessageID")[0].firstChild.data.strip())
    env.setTo(dom.getElementsByTagNameNS(NS_A, "To")[0].firstChild.data.strip())

    _parseAppSequence(dom, env)

    relatesToNodes = dom.getElementsByTagNameNS(NS_A, "RelatesTo")
    if len(relatesToNodes) > 0:
        env.setRelatesTo(relatesToNodes[0].firstChild.data.strip())
        env.setRelationshipType(getQNameFromValue( \
            relatesToNodes[0].getAttribute("RelationshipType"), relatesToNodes[0]))

    env.setEPR(dom.getElementsByTagNameNS(NS_A, "Address")[0].firstChild.data.strip())

    typeNodes = dom.getElementsByTagNameNS(NS_D, "Types")
    if len(typeNodes) > 0:
        env.setTypes(getTypes(typeNodes[0]))

    scopeNodes = dom.getElementsByTagNameNS(NS_D, "Scopes")
    if len(scopeNodes) > 0:
        env.setScopes(getScopes(scopeNodes[0]))

    xNodes = dom.getElementsByTagNameNS(NS_D, "XAddrs")
    if len(xNodes) > 0:
        env.setXAddrs(getXAddrs(xNodes[0]))
        
    env.setMetadataVersion(dom.getElementsByTagNameNS(NS_D, "MetadataVersion")[0].firstChild.data.strip())
    
    return env

def parseByeMessage(dom):
    env = SoapEnvelope()
    env.setAction(ACTION_BYE)

    env.setMessageId(dom.getElementsByTagNameNS(NS_A, "MessageID")[0].firstChild.data.strip())
    env.setTo(dom.getElementsByTagNameNS(NS_A, "To")[0].firstChild.data.strip())

    _parseAppSequence(dom, env)
    
    env.setEPR(dom.getElementsByTagNameNS(NS_A, "Address")[0].firstChild.data.strip())
    
    return env

def parseEnvelope(data, ipAddr):
    try:
        dom = minidom.parseString(data)
    except Exception as ex:
        #print >> sys.stderr, 'Failed to parse message from %s\n"%s": %s' % (ipAddr, data, ex)
        return None
    
    if dom.getElementsByTagNameNS(NS_S, "Fault"):
        #print >> sys.stderr, 'Fault received from %s:' % (ipAddr, data)
        return None
    
    soapAction = dom.getElementsByTagNameNS(NS_A, "Action")[0].firstChild.data.strip()
    if soapAction == ACTION_PROBE:
        return parseProbeMessage(dom)
    elif soapAction == ACTION_PROBE_MATCH:
        return parseProbeMatchMessage(dom)
    elif soapAction == ACTION_RESOLVE:
        return parseResolveMessage(dom)
    elif soapAction == ACTION_RESOLVE_MATCH:
        return parseResolveMatchMessage(dom)
    elif soapAction == ACTION_BYE:
        return parseByeMessage(dom)
    elif soapAction == ACTION_HELLO:
        return parseHelloMessage(dom)

def createMessage(env):
    if env.getAction() == ACTION_PROBE:
        return createProbeMessage(env)
    if env.getAction() == ACTION_PROBE_MATCH:
        return createProbeMatchMessage(env)
    if env.getAction() == ACTION_RESOLVE:
        return createResolveMessage(env)
    if env.getAction() == ACTION_RESOLVE_MATCH:
        return createResolveMatchMessage(env)
    if env.getAction() == ACTION_HELLO:
        return createHelloMessage(env)
    if env.getAction() == ACTION_BYE:
        return createByeMessage(env)

def createProbeMessage(env):
    doc = createSkelSoapMessage(ACTION_PROBE)

    bodyEl = getBodyEl(doc)
    headerEl = getHeaderEl(doc)

    addElementWithText(doc, headerEl, "a:MessageID", NS_A, env.getMessageId())
    addElementWithText(doc, headerEl, "a:To", NS_A, env.getTo())

    if len(env.getReplyTo()) > 0:
        addElementWithText(doc, headerEl, "a:ReplyTo", NS_A, env.getReplyTo())

    probeEl = doc.createElementNS(NS_D, "d:Probe")
    bodyEl.appendChild(probeEl)

    addTypes(doc, probeEl, env.getTypes())
    addScopes(doc, probeEl, env.getScopes())
    
    return getDocAsString(doc)

def createProbeMatchMessage(env):
    doc = createSkelSoapMessage(ACTION_PROBE_MATCH)

    bodyEl = getBodyEl(doc)
    headerEl = getHeaderEl(doc)

    addElementWithText(doc, headerEl, "a:MessageID", NS_A, env.getMessageId())
    addElementWithText(doc, headerEl, "a:RelatesTo", NS_A, env.getRelatesTo())
    addElementWithText(doc, headerEl, "a:To", NS_A, env.getTo())

    appSeqEl = doc.createElementNS(NS_D, "d:AppSequence")
    appSeqEl.setAttribute("InstanceId", env.getInstanceId())
    appSeqEl.setAttribute("MessageNumber", env.getMessageNumber())
    headerEl.appendChild(appSeqEl)

    probeMatchesEl = doc.createElementNS(NS_D, "d:ProbeMatches")
    probeMatches = env.getProbeResolveMatches()
    for probeMatch in probeMatches:
        probeMatchEl = doc.createElementNS(NS_D, "d:ProbeMatch")
        addEPR(doc, probeMatchEl, probeMatch.getEPR())
        addTypes(doc, probeMatchEl, probeMatch.getTypes())
        addScopes(doc, probeMatchEl, probeMatch.getScopes())
        addXAddrs(doc, probeMatchEl, probeMatch.getXAddrs())
        addElementWithText(doc, probeMatchEl, "d:MetadataVersion", NS_D, probeMatch.getMetadataVersion())
        probeMatchesEl.appendChild(probeMatchEl)
    
    
    bodyEl.appendChild(probeMatchesEl)

    return getDocAsString(doc)

def createResolveMessage(env):
    doc = createSkelSoapMessage(ACTION_RESOLVE)

    bodyEl = getBodyEl(doc)
    headerEl = getHeaderEl(doc)

    addElementWithText(doc, headerEl, "a:MessageID", NS_A, env.getMessageId())
    addElementWithText(doc, headerEl, "a:To", NS_A, env.getTo())

    if len(env.getReplyTo()) > 0:
        addElementWithText(doc, headerEl, "a:ReplyTo", NS_A, env.getReplyTo())

    resolveEl = doc.createElementNS(NS_D, "d:Resolve")
    addEPR(doc, resolveEl, env.getEPR())
    bodyEl.appendChild(resolveEl)

    return getDocAsString(doc)    

def createResolveMatchMessage(env):
    doc = createSkelSoapMessage(ACTION_RESOLVE_MATCH)

    bodyEl = getBodyEl(doc)
    headerEl = getHeaderEl(doc)

    addElementWithText(doc, headerEl, "a:MessageID", NS_A, env.getMessageId())
    addElementWithText(doc, headerEl, "a:RelatesTo", NS_A, env.getRelatesTo())
    addElementWithText(doc, headerEl, "a:To", NS_A, env.getTo())

    appSeqEl = doc.createElementNS(NS_D, "d:AppSequence")
    appSeqEl.setAttribute("InstanceId", env.getInstanceId())
    appSeqEl.setAttribute("MessageNumber", env.getMessageNumber())
    headerEl.appendChild(appSeqEl)

    resolveMatchesEl = doc.createElementNS(NS_D, "d:ResolveMatches")
    if len(env.getProbeResolveMatches()) > 0:
        resolveMatch = env.getProbeResolveMatches()[0]
        resolveMatchEl = doc.createElementNS(NS_D, "d:ResolveMatch")
        addEPR(doc, resolveMatchEl, resolveMatch.getEPR())
        addTypes(doc, resolveMatchEl, resolveMatch.getTypes())
        addScopes(doc, resolveMatchEl, resolveMatch.getScopes())
        addXAddrs(doc, resolveMatchEl, resolveMatch.getXAddrs())
        addElementWithText(doc, resolveMatchEl, "d:MetadataVersion", NS_D, resolveMatch.getMetadataVersion())
        
        resolveMatchesEl.appendChild(resolveMatchEl)

    bodyEl.appendChild(resolveMatchesEl)
    
    return getDocAsString(doc)

def createHelloMessage(env):
    doc = createSkelSoapMessage(ACTION_HELLO)

    bodyEl = getBodyEl(doc)
    headerEl = getHeaderEl(doc)

    addElementWithText(doc, headerEl, "a:MessageID", NS_A, env.getMessageId())

    if len(env.getRelatesTo()) > 0:
        addElementWithText(doc, headerEl, "a:RelatesTo", NS_A, env.getRelatesTo())
        relatesToEl = headerEl.getElementsByTagNameNS(NS_A, "RelatesTo")[0]
        relatesToEl.setAttribute("RelationshipType", "d:Suppression")

    addElementWithText(doc, headerEl, "a:To", NS_A, env.getTo())

    appSeqEl = doc.createElementNS(NS_D, "d:AppSequence")
    appSeqEl.setAttribute("InstanceId", env.getInstanceId())
    appSeqEl.setAttribute("MessageNumber", env.getMessageNumber())
    headerEl.appendChild(appSeqEl)

    helloEl = doc.createElementNS(NS_D, "d:Hello")
    addEPR(doc, helloEl, env.getEPR())
    addTypes(doc, helloEl, env.getTypes())
    addScopes(doc, helloEl, env.getScopes())
    addXAddrs(doc, helloEl, env.getXAddrs())
    addElementWithText(doc, helloEl, "d:MetadataVersion", NS_D, env.getMetadataVersion())

    bodyEl.appendChild(helloEl)
    
    return getDocAsString(doc)

def createByeMessage(env):
    doc = createSkelSoapMessage(ACTION_BYE)

    bodyEl = getBodyEl(doc)
    headerEl = getHeaderEl(doc)

    addElementWithText(doc, headerEl, "a:MessageID", NS_A, env.getMessageId())
    addElementWithText(doc, headerEl, "a:To", NS_A, env.getTo())

    appSeqEl = doc.createElementNS(NS_D, "d:AppSequence")
    appSeqEl.setAttribute("InstanceId", env.getInstanceId())
    appSeqEl.setAttribute("MessageNumber", env.getMessageNumber())
    headerEl.appendChild(appSeqEl)

    byeEl = doc.createElementNS(NS_D, "d:Bye")
    addEPR(doc, byeEl, env.getEPR())
    bodyEl.appendChild(byeEl)

    return getDocAsString(doc)

def extractSoapUdpAddressFromURI(uri):
    val = uri.getPathExQueryFragment().split(":")
    part1 = val[0][2:]
    part2 = None
    if val[1].count('/') > 0:
        part2 = int(val[1][:val[1].index('/')])
    else:
        part2 = int(val[1])
    addr = [part1, part2]
    return addr


class AddressMonitorThread(_StopableDaemonThread):
    def __init__(self, wsd):
        self._addrs = set()
        self._wsd = wsd
        super(AddressMonitorThread, self).__init__()
        self._updateAddrs()
    
    def _updateAddrs(self):
        addrs = set(_getNetworkAddrs())
        
        disappeared = self._addrs.difference(addrs)
        new = addrs.difference(self._addrs)
        
        for addr in disappeared:
            self._wsd._networkAddressRemoved(addr)
        
        for addr in new:
            self._wsd._networkAddressAdded(addr)
        
        self._addrs = addrs

    def run(self):
        while not self._quitEvent.wait(_NETWORK_ADDRESSES_CHECK_TIMEOUT):
            self._updateAddrs()


class NetworkingThread(_StopableDaemonThread):
    def __init__(self, observer):
        super(NetworkingThread, self).__init__()
        
        self.setDaemon(True)
        self._queue = []    # FIXME synchronisation

        self._knownMessageIds = set()
        self._iidMap = {}
        self._observer = observer
        
        self._poll = select.poll()

    @staticmethod
    def _makeMreq(addr):
        return struct.pack("4s4s", socket.inet_aton(MULTICAST_IPV4_ADDRESS), socket.inet_aton(addr))

    @staticmethod
    def _createMulticastOutSocket(addr):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setblocking(0)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
        if addr is None:
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.INADDR_ANY)
        else:
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(addr))
        
        return sock

    @staticmethod
    def _createMulticastInSocket():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        sock.bind(('', MULTICAST_PORT))
    
        sock.setblocking(0)
    
        return sock
    
    def addSourceAddr(self, addr):
        """None means 'system default'"""
        try:
            self._multiInSocket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, self._makeMreq(addr))
        except socket.error:  # if 1 interface has more than 1 address, exception is raised for the second
            pass
        
        sock = self._createMulticastOutSocket(addr)
        self._multiOutUniInSockets[addr] = sock
        self._poll.register(sock, select.POLLIN)
    
    def removeSourceAddr(self, addr):
        try:
            self._multiInSocket.setsockopt(socket.IPPROTO_IP, socket.IP_DROP_MEMBERSHIP, self._makeMreq(addr))
        except socket.error:  # see comments for setsockopt(.., socket.IP_ADD_MEMBERSHIP..
            pass

        sock = self._multiOutUniInSockets[addr]
        self._poll.unregister(sock)
        sock.close()
        del self._multiOutUniInSockets[addr]

    def addUnicastMessage(self, env, addr, port, initialDelay=0):
        msg = Message(env, addr, port, Message.UNICAST, initialDelay)
        
        self._queue.append(msg)
        self._knownMessageIds.add(env.getMessageId())
    
    def addMulticastMessage(self, env, addr, port, initialDelay=0):
        msg = Message(env, addr, port, Message.MULTICAST, initialDelay)
        
        self._queue.append(msg)
        self._knownMessageIds.add(env.getMessageId())

    def run(self):
        while not self._quitEvent.is_set() or self._queue:
            self._sendPendingMessages()
            self._recvMessages()
    
    def _recvMessages(self):
        for fd, event in self._poll.poll(0):
            sock = socket.fromfd(fd, socket.AF_INET, socket.SOCK_DGRAM)
            
            try:
                data, addr = sock.recvfrom(BUFFER_SIZE)
            except socket.error, e:
                time.sleep(0.01)
                continue
    
            env = parseEnvelope(data, addr[0])
        
            if env is None: # fault or failed to parse
                continue
            
            mid = env.getMessageId()
            if mid in self._knownMessageIds:
                continue
            else:
                self._knownMessageIds.add(mid)
            
            iid = env.getInstanceId()
            mid = env.getMessageId()
            if iid > 0:
                mnum = env.getMessageNumber()
                key = addr[0] + ":" + str(addr[1]) + ":" + str(iid)
                if mid is not None and len(mid) > 0:
                    key = key + ":" + mid
                if not self._iidMap.has_key(key):
                    self._iidMap[key] = iid
                else:
                    tmnum = self._iidMap[key]
                    if mnum > tmnum:
                        self._iidMap[key] = mnum
                    else:
                        continue
        
            self._observer.envReceived(env, addr)
    
    def _sendMsg(self, msg):
        data = createMessage(msg.getEnv())

        if msg.msgType() == Message.UNICAST:
            self._uniOutSocket.sendto(data, (msg.getAddr(), msg.getPort()))
        else:
            for sock in self._multiOutUniInSockets.values():
                sock.sendto(data, (msg.getAddr(), msg.getPort()))

    def _sendPendingMessages(self):
        """Method sleeps, if nothing to do"""
        if len(self._queue) == 0:
            time.sleep(0.1)
            return
        msg = self._queue.pop(0)
        if msg.canSend():
            self._sendMsg(msg)
            msg.refresh()
            if not (msg.isFinished()):
                self._queue.append(msg)
        else:
            self._queue.append(msg)
            time.sleep(0.01)

    def start(self):
        super(NetworkingThread, self).start()
        
        self._uniOutSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        self._multiInSocket = self._createMulticastInSocket()
        self._poll.register(self._multiInSocket)
        
        self._multiOutUniInSockets = {}  # FIXME synchronisation
        
    def join(self):
        super(NetworkingThread, self).join()
        self._uniOutSocket.close()
        
        self._poll.unregister(self._multiInSocket)
        self._multiInSocket.close()


class Message:
    MULTICAST = 'multicast'
    UNICAST = 'unicast'

    def __init__(self, env, addr, port, msgType, initialDelay=0):
        """msgType shall be Message.MULTICAST or Message.UNICAST"""
        self._env = env
        self._addr = addr
        self._port = port
        self._msgType = msgType
        
        if msgType == self.UNICAST:
            udpRepeat, udpMinDelay, udpMaxDelay, udpUpperDelay = \
                    UNICAST_UDP_REPEAT, \
                    UNICAST_UDP_MIN_DELAY, \
                    UNICAST_UDP_MAX_DELAY, \
                    UNICAST_UDP_UPPER_DELAY
        else:
            udpRepeat, udpMinDelay, udpMaxDelay, udpUpperDelay = \
                    MULTICAST_UDP_REPEAT, \
                    MULTICAST_UDP_MIN_DELAY, \
                    MULTICAST_UDP_MAX_DELAY, \
                    MULTICAST_UDP_UPPER_DELAY

        self._udpRepeat = udpRepeat
        self._udpUpperDelay = udpUpperDelay
        self._t = (udpMinDelay + ((udpMaxDelay - udpMinDelay) * random.random())) / 2
        self._nextTime = int(time.time() * 1000) + initialDelay

    def getEnv(self):
        return self._env

    def getAddr(self):
        return self._addr

    def getPort(self):
        return self._port
    
    def msgType(self):
        return self._msgType
    
    def isFinished(self):
        return self._udpRepeat <= 0

    def canSend(self):
        ct = int(time.time() * 1000)
        return self._nextTime < ct

    def refresh(self):
        self._t = self._t * 2
        if self._t > self._udpUpperDelay:
            self._t = self._udpUpperDelay
        self._nextTime = int(time.time() * 1000) + self._t
        self._udpRepeat = self._udpRepeat - 1

class Service:

    def __init__(self, types, scopes, xAddrs, epr, instanceId):
        self._types = types
        self._scopes = scopes
        self._xAddrs = xAddrs
        self._epr = epr
        self._instanceId = instanceId
        self._messageNumber = 0
        self._metadataVersion = 1

    def getTypes(self):
        return self._types

    def setTypes(self, types):
        self._types = types

    def getScopes(self):
        return self._scopes

    def setScopes(self, scopes):
        self._scopes = scopes

    def getXAddrs(self):
        ret = []
        ipAddrs = None
        for xAddr in self._xAddrs:
            if '{ip}' in xAddr:
                if ipAddrs is None:
                    ipAddrs = _getNetworkAddrs()
                for ipAddr in ipAddrs:
                    if ipAddr != '127.0.0.1':
                        ret.append(xAddr.format(ip=ipAddr))
            else:
                ret.append(xAddr)
        return ret

    def setXAddrs(self, xAddrs):
        self._xAddrs = xAddrs

    def getEPR(self):
        return self._epr

    def setEPR(self, epr):
        self._epr = epr

    def getInstanceId(self):
        return self._instanceId

    def setInstanceId(self, instanceId):
        self._instanceId = instanceId

    def getMessageNumber(self):
        return self._messageNumber

    def setMessageNumber(self, messageNumber):
        self._messageNumber = messageNumber

    def getMetadataVersion(self):
        return self._metadataVersion

    def setMetadataVersion(self, metadataVersion):
        self._metadataVersion = metadataVersion

    def incrementMessageNumber(self):
        self._messageNumber = self._messageNumber + 1
        

class WSDiscovery:

    def __init__(self, uuid_=None):
        
        self._networkingThread = None
        self._serverStarted = False
        self._remoteServices = {}
        self._localServices = {}

        self._dpActive = False
        self._dpAddr = None
        self._dpEPR = None
        
        self._remoteServiceHelloCallback = None
        self._remoteServiceHelloCallbackTypesFilter = None
        self._remoteServiceHelloCallbackScopesFilter = None
        self._remoteServiceByeCallback = None
        
        if uuid_ is not None:
            self.uuid = uuid_
        else:
            self.uuid = uuid.uuid4().get_urn()

    def setRemoteServiceHelloCallback(self, cb, types=None, scopes=None):
        """Set callback, which will be called when new service appeared online
        and sent Hi message
        
        typesFilter and scopesFilter might be list of types and scopes.
        If filter is set, callback is called only for Hello messages,
        which match filter
        
        Set None to disable callback
        """
        self._remoteServiceHelloCallback = cb
        self._remoteServiceHelloCallbackTypesFilter = types
        self._remoteServiceHelloCallbackScopesFilter = scopes

    def setRemoteServiceByeCallback(self, cb):
        """Set callback, which will be called when new service appeared online
        and sent Hi message
        Service is passed as a parameter to the callback
        Set None to disable callback
        """
        self._remoteServiceByeCallback = cb

    def setRemoveServiceDisappearedCallback(self, cb):
        """Set callback, which will be called when new service disappears
        Service uuid is passed as a parameter to the callback
        Set None to disable callback
        """
        self._remoteServiceDisppearedCallback = cb

    def _addRemoteService(self, service):
        self._remoteServices[service.getEPR()] = service

    def _removeRemoteService(self, epr):
        if self._remoteServices.has_key(epr):
            del self._remoteServices[epr]

    def handleEnv(self, env, addr):        
        if (env.getAction() == ACTION_PROBE_MATCH):
            for match in env.getProbeResolveMatches():
                self._addRemoteService(Service(match.getTypes(), match.getScopes(), match.getXAddrs(), match.getEPR(), 0))
                if match.getXAddrs() is None or len(match.getXAddrs()) == 0:
                    self._sendResolve(match.getEPR())
                    
        elif env.getAction() == ACTION_RESOLVE_MATCH:
            for match in env.getProbeResolveMatches():
                self._addRemoteService(Service(match.getTypes(), match.getScopes(), match.getXAddrs(), match.getEPR(), 0))

        elif env.getAction() == ACTION_PROBE:
            services = self._filterServices(self._localServices.values(), env.getTypes(), env.getScopes())
            self._sendProbeMatch(services, env.getMessageId(), addr)

        elif env.getAction() == ACTION_RESOLVE:
            if self._localServices.has_key(env.getEPR()):
                service = self._localServices[env.getEPR()]
                self._sendResolveMatch(service, env.getMessageId(), addr)

        elif env.getAction() == ACTION_HELLO:
            #check if it is from a discovery proxy
            rt = env.getRelationshipType()
            if rt is not None and rt.getLocalname() == "Suppression" and rt.getNamespace() == NS_D:
                xAddr = env.getXAddrs()[0]
                #only support 'soap.udp'
                if xAddr.startswith("soap.udp:"):
                    self._dpActive = True
                    self._dpAddr = extractSoapUdpAddressFromURI(URI(xAddr))
                    self._dpEPR = env.getEPR()

            service = Service(env.getTypes(), env.getScopes(), env.getXAddrs(), env.getEPR(), 0)
            self._addRemoteService(service)
            if self._remoteServiceHelloCallback is not None:
                if self._matchesFilter(service,
                                        self._remoteServiceHelloCallbackTypesFilter,
                                        self._remoteServiceHelloCallbackScopesFilter):
                    self._remoteServiceHelloCallback(service)

        elif env.getAction() == ACTION_BYE:
            #if the bye is from discovery proxy... revert back to multicasting
            if self._dpActive and self._dpEPR == env.getEPR():
                self._dpActive = False
                self._dpAddr = None
                self._dpEPR = None
            
            self._removeRemoteService(env.getEPR())
            if self._remoteServiceByeCallback is not None:
                self._remoteServiceByeCallback(env.getEPR())

    def envReceived(self, env, addr):
        self.handleEnv(env, addr)

    def _sendResolveMatch(self, service, relatesTo, addr):
        service.incrementMessageNumber()
        
        env = SoapEnvelope()
        env.setAction(ACTION_RESOLVE_MATCH)
        env.setTo(ADDRESS_UNKNOWN)
        env.setMessageId(uuid.uuid4().get_urn())
        env.setInstanceId(str(service.getInstanceId()))
        env.setMessageNumber(str(service.getMessageNumber()))
        env.setRelatesTo(relatesTo)

        env.getProbeResolveMatches().append(ProbeResolveMatch(service.getEPR(), \
                                                              service.getTypes(), service.getScopes(), \
                                                              service.getXAddrs(), str(service.getMetadataVersion())))
        self._networkingThread.addUnicastMessage(env, addr[0], addr[1])

    def _sendProbeMatch(self, services, relatesTo, addr):
        env = SoapEnvelope()
        env.setAction(ACTION_PROBE_MATCH)
        env.setTo(ADDRESS_UNKNOWN)
        env.setMessageId(uuid.uuid4().get_urn())
        random.seed((int)(time.time() * 1000000))
        env.setInstanceId(_generateInstanceId())
        env.setMessageNumber("1")
        env.setRelatesTo(relatesTo)

        for service in services:
            env.getProbeResolveMatches().append(ProbeResolveMatch(service.getEPR(), \
                                                                  service.getTypes(), service.getScopes(), \
                                                                  service.getXAddrs(), str(service.getMetadataVersion())))

        self._networkingThread.addUnicastMessage(env, addr[0], addr[1], random.randint(0, APP_MAX_DELAY))

    def _sendProbe(self, types=None, scopes=None):
        env = SoapEnvelope()
        env.setAction(ACTION_PROBE)
        env.setTo(ADDRESS_ALL)
        env.setMessageId(uuid.uuid4().get_urn())
        env.setTypes(types)
        env.setScopes(scopes)

        if self._dpActive:
            self._networkingThread.addUnicastMessage(env, self._dpAddr[0], self._dpAddr[1])
        else:
            self._networkingThread.addMulticastMessage(env, MULTICAST_IPV4_ADDRESS, MULTICAST_PORT)

    def _sendResolve(self, epr):
        env = SoapEnvelope()
        env.setAction(ACTION_RESOLVE)
        env.setTo(ADDRESS_ALL)
        env.setMessageId(uuid.uuid4().get_urn())
        env.setEPR(epr)

        if self._dpActive:
            self._networkingThread.addUnicastMessage(env, self._dpAddr[0], self._dpAddr[1])
        else:
            self._networkingThread.addMulticastMessage(env, MULTICAST_IPV4_ADDRESS, MULTICAST_PORT)

    def _sendHello(self, service):
        service.incrementMessageNumber()

        env = SoapEnvelope()
        env.setAction(ACTION_HELLO)
        env.setTo(ADDRESS_ALL)
        env.setMessageId(uuid.uuid4().get_urn())
        env.setInstanceId(str(service.getInstanceId()))
        env.setMessageNumber(str(service.getMessageNumber()))
        env.setTypes(service.getTypes())
        env.setScopes(service.getScopes())
        env.setXAddrs(service.getXAddrs())
        env.setEPR(service.getEPR())

        random.seed((int)(time.time() * 1000000))

        self._networkingThread.addMulticastMessage(env, MULTICAST_IPV4_ADDRESS, MULTICAST_PORT, random.randint(0, APP_MAX_DELAY))

    def _sendBye(self, service):
        env = SoapEnvelope()
        env.setAction(ACTION_BYE)
        env.setTo(ADDRESS_ALL)
        env.setMessageId(uuid.uuid4().get_urn())
        env.setInstanceId(str(service.getInstanceId()))
        env.setMessageNumber(str(service.getMessageNumber()))
        env.setEPR(service.getEPR())

        service.incrementMessageNumber()
        self._networkingThread.addMulticastMessage(env, MULTICAST_IPV4_ADDRESS, MULTICAST_PORT)

    def start(self):
        'start the discovery server - should be called before using other functions'
        self._startThreads()
        self._serverStarted = True

    def stop(self):
        'cleans up and stops the discovery server'

        self.clearRemoteServices()
        self.clearLocalServices()

        self._stopThreads()
        self._serverStarted = False

    def  _networkAddressAdded(self, addr):
        self._networkingThread.addSourceAddr(addr)
        for service in self._localServices.values():
            self._sendHello(service)

    def _networkAddressRemoved(self, addr):
        self._networkingThread.removeSourceAddr(addr)

    def _startThreads(self):
        if self._networkingThread is not None:
            return
        
        self._networkingThread = NetworkingThread(self)
        self._networkingThread.start()

        self._addrsMonitorThread = AddressMonitorThread(self)
        self._addrsMonitorThread.start()
    

    def _stopThreads(self):
        if self._networkingThread is None:
            return

        self._networkingThread.schedule_stop()
        self._addrsMonitorThread.schedule_stop()
        
        self._networkingThread.join()
        self._addrsMonitorThread.join()
        
        self._networkingThread = None

    def _isTypeInList(self, ttype, types):
        for entry in types:
            if matchType(ttype, entry):
                return True
            
        return False
    
    def _isScopeInList(self, scope, scopes):
        for entry in scopes:
            if matchScope(scope.getValue(), entry.getValue(), scope.getMatchBy()):
                return True
            
        return False

    def _matchesFilter(self, service, types, scopes):
        if types is not None:
            for ttype in types:
                if not self._isTypeInList(ttype, service.getTypes()):
                    return False
        if scopes is not None:
            for scope in scopes:
                if not self._isScopeInList(scope, service.getScopes()):
                    return False
        return True

    def _filterServices(self, services, types, scopes):
        return [service for service in services \
                    if self._matchesFilter(service, types, scopes)]

    def clearRemoteServices(self):
        'clears remotely discovered services'
        
        self._remoteServices.clear()

    def clearLocalServices(self):
        'send Bye messages for the services and remove them'
        
        for service in self._localServices.values():
            self._sendBye(service)

        self._localServices.clear()

    def searchServices(self, types=None, scopes=None, timeout=3):
        'search for services given the TYPES and SCOPES in a given TIMEOUT'
        
        if not self._serverStarted:
            raise Exception("Server not started")

        self._sendProbe(types, scopes)
        
        time.sleep(timeout)

        return self._filterServices(self._remoteServices.values(), types, scopes)

    def publishService(self, types, scopes, xAddrs):
        """Publish a service with the given TYPES, SCOPES and XAddrs (service addresses)
        
        if xAddrs contains item, which includes {ip} pattern, one item per IP addres will be sent
        """
        
        if not self._serverStarted:
            raise Exception("Server not started")
        
        instanceId = _generateInstanceId()
        
        service = Service(types, scopes, xAddrs, self.uuid, instanceId)
        self._localServices[self.uuid] = service
        self._sendHello(service)
        
        time.sleep(0.001)
 
def showEnv(env):
    print "-----------------------------"
    print "Action: %s" % env.getAction()
    print "MessageId: %s" % env.getMessageId()
    print "InstanceId: %s" % env.getInstanceId()
    print "MessageNumber: %s" % env.getMessageNumber()
    print "Reply To: %s" % env.getReplyTo()
    print "To: %s" % env.getTo()
    print "RelatesTo: %s" % env.getRelatesTo()
    print "Relationship Type: %s" % env.getRelationshipType()
    print "Types: %s" % env.getTypes()
    print "Scopes: %s" % env.getScopes()
    print "EPR: %s" % env.getEPR()
    print "Metadata Version: %s" % env.getMetadataVersion()
    print "Probe Matches: %s" % env.getProbeResolveMatches()
    print "-----------------------------"
    
if __name__ == "__main__":
    wsd = WSDiscovery()
    wsd.start()

    ttype = QName("abc", "def")

    ttype1 = QName("namespace", "myTestService")
    scope1 = Scope("http://myscope")
    ttype2 = QName("namespace", "myOtherTestService_type1")
    scope2 = Scope("http://other_scope")
    
    xAddrs = ["localhost:8080/abc", '{ip}/device_service']
    wsd.publishService(types=[ttype], scopes=[scope2], xAddrs=xAddrs)
    
    #ret = wsd.searchServices(scopes=[scope1], timeout=10)
    ret = wsd.searchServices()
    
    for service in ret:
        print service.getEPR() + ":" + service.getXAddrs()[0]

    wsd.stop()
