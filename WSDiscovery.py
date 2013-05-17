import urllib
from xml.dom import minidom
import xml.dom.ext
import StringIO
import random
import string
import socket
import struct
import time
import uuid
import threading
import thread

BUFFER_SIZE = 0xffff
APP_MAX_DELAY = 500 # miliseconds
DP_MAX_TIMEOUT = 5000 # 5 seconds
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

class URI:

    def __init__(self, uri):
        uri = urllib.unquote(uri)
        i1 = uri.find(":")
        i2 = uri.find("@")
        self.__scheme = uri[:i1]
        if i2 != -1:
            self.__authority = uri[i1 + 1: i2]
            self.__path = uri[i2 + 1:]
        else:
            self.__authority = ""
            self.__path = uri[i1 + 1:]

    def getScheme(self):
        return self.__scheme

    def getAuthority(self):
        return self.__authority

    def getPath(self):
        return self.__path

    def getPathExQueryFragment(self):
        i = self.__path.find("?")
        path = self.getPath()
        if i != -1:
            return path[:self.__path.find("?")]
        else:
            return path

class QName:

    def __init__(self, namespace, localname):        
        self.__namespace = namespace
        self.__localname = localname

    def getNamespace(self):
        return self.__namespace

    def getLocalname(self):
        return self.__localname

    def getFullname(self):
        return self.getNamespace() + ":" + self.getLocalname()

    def __repr__(self):
        return self.getFullname()
        

class Scope:

    def __init__(self, value, matchBy=None):
        self.__matchBy = matchBy
        self.__value = value

    def getMatchBy(self):
        return self.__matchBy

    def getValue(self):
        return self.__value

    def __repr__(self):
        if self.getMatchBy() == None or len(self.getMatchBy()) == 0:
            return self.getValue()
        else:
            return self.getMatchBy() + ":" + self.getValue()

class ProbeResolveMatch:

    def __init__(self, epr, types, scopes, xAddrs, metadataVersion):
        self.__epr = epr
        self.__types = types
        self.__scopes = scopes
        self.__xAddrs = xAddrs
        self.__metadataVersion = metadataVersion
        
    def getEPR(self):
        return self.__epr

    def getTypes(self):
        return self.__types

    def getScopes(self):
        return self.__scopes

    def getXAddrs(self):
        return self.__xAddrs

    def getMetadataVersion(self):
        return self.__metadataVersion

    def __repr__(self):
        return "EPR: %s\nTypes: %s\nScopes: %s\nXAddrs: %s\nMetadata Version: %s" % \
            (self.getEPR(), self.getTypes(), self.getScopes(),
             self.getXAddrs(), self.getMetadataVersion())

class SoapEnvelope:

    def __init__(self):
        self.__action = ""
        self.__messageId = ""
        self.__relatesTo = ""
        self.__relationshipType = None
        self.__to = ""
        self.__replyTo = ""
        self.__instanceId = ""
        self.__sequenceId = ""
        self.__messageNumber = ""
        self.__epr = ""
        self.__types = []
        self.__scopes = []
        self.__xAddrs = []
        self.__metadataVersion = ""
        self.__probeResolveMatches = []

    def getAction(self):
        return self.__action

    def setAction(self, action):
        self.__action = action

    def getMessageId(self):
        return self.__messageId

    def setMessageId(self, messageId):
        self.__messageId = messageId

    def getRelatesTo(self):
        return self.__relatesTo

    def setRelatesTo(self, relatesTo):
        self.__relatesTo = relatesTo

    def getRelationshipType(self):
        return self.__relationshipType

    def setRelationshipType(self, relationshipType):
        self.__relationshipType = relationshipType

    def getTo(self):
        return self.__to
    
    def setTo(self, to):
        self.__to = to

    def getReplyTo(self):
        return self.__replyTo
    
    def setReplyTo(self, replyTo):
        self.__replyTo = replyTo

    def getInstanceId(self):
        return self.__instanceId

    def setInstanceId(self, instanceId):
        self.__instanceId = instanceId

    def getSequenceId(self):
        return self.__sequenceId

    def setSequenceId(self, sequenceId):
        self.__sequenceId = sequenceId
        
    def getEPR(self):
        return self.__epr

    def setEPR(self, epr):
        self.__epr = epr

    def getMessageNumber(self):
        return self.__messageNumber

    def setMessageNumber(self, messageNumber):
        self.__messageNumber = messageNumber

    def getTypes(self):
        return self.__types

    def setTypes(self, types):
        self.__types = types

    def getScopes(self):
        return self.__scopes

    def setScopes(self, scopes):
        self.__scopes = scopes

    def getXAddrs(self):
        return self.__xAddrs

    def setXAddrs(self, xAddrs):
        self.__xAddrs = xAddrs

    def getMetadataVersion(self):
        return self.__metadataVersion

    def setMetadataVersion(self, metadataVersion):
        self.__metadataVersion = metadataVersion

    def getProbeResolveMatches(self):
        return self.__probeResolveMatches

    def setProbeResolveMatches(self, probeResolveMatches):
        self.__probeResolveMatches = probeResolveMatches


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
    

def getTypes(typeNode):
    ret = []

    if len(typeNode.childNodes) > 0:
        items = typeNode.childNodes[0].data.split(" ")
        
        for item in items:
            item = item.strip()
            if len(item) == 0:
                continue
            ret.append(getQNameFromValue(item, typeNode))
        
    return ret

def getScopes(scopeNode):
    ret = []
    matchBy = scopeNode.getAttribute("MatchBy")

    if len(scopeNode.childNodes) > 0:
        items = scopeNode.childNodes[0].data.split(" ")
        
        for item in items:
            item = item.strip()
            if len(item) == 0:
                continue            
            ret.append(Scope(item, matchBy))

    return ret

def getXAddrs(xAddrsNode):
    ret = []

    if len(xAddrsNode.childNodes) > 0:
        items = xAddrsNode.childNodes[0].data.split(" ")
        
        for item in items:
            item = item.strip()
            if len(item) == 0:
                continue            
            ret.append(item)

    return ret

def createSkelSoapMessage(soapAction):
    doc = minidom.Document()

    envEl = doc.createElementNS(NS_S, "s:Envelope")
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
    xml.dom.ext.PrettyPrint(doc, stream)    
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
        addElementWithText(doc, node, "d:Scopes", NS_D, " ".join([x.getValue() for x in scopes]))
        if scopes[0].getMatchBy() is not None and len(scopes[0].getMatchBy()) > 0:
            node.getElementsByTagNameNS(NS_D, "Scopes")[0].setAttribute("MatchBy", scopes[0].getMatchBy())

def addXAddrs(doc, node, xAddrs):
    if xAddrs is not len(xAddrs) > 0:
        addElementWithText(doc, node, "d:XAddrs", NS_D, " ".join([x for x in xAddrs]))

def addEPR(doc, node, epr):
    eprEl = doc.createElementNS(NS_A, "a:EndpointReference")
    addElementWithText(doc, eprEl, "a:Address", NS_A, epr)
    node.appendChild(eprEl)

def createMulticastOutSocket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
    sock.setblocking(0)
    return sock

def createMulticastInSocket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', MULTICAST_PORT))
    mreq = struct.pack("4sl", socket.inet_aton(MULTICAST_IPV4_ADDRESS), socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    sock.setblocking(0)

    return sock

def createUnicastOutSocket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return sock

def readMessage(sock):
        try:
            data, addr = sock.recvfrom(BUFFER_SIZE)
        except socket.error, e:
            return None
        else:
            return (data, addr)

def parseProbeMessage(dom):
    env = SoapEnvelope()
    env.setAction(ACTION_PROBE)
    env.setMessageId(dom.getElementsByTagNameNS(NS_A, "MessageID")[0].firstChild.data.strip())

    replyToNodes = dom.getElementsByTagNameNS(NS_A, "ReplyTo")
    if len(replyToNodes) > 0:
        env.setReplyTo(replyToNodes[0].firstChild.data.strip())

    env.setTo(dom.getElementsByTagNameNS(NS_A, "To")[0].firstChild.data.strip())

    typeNodes = dom.getElementsByTagNameNS(NS_D, "Types")
    if len(typeNodes) > 0:
        env.getTypes().extend(getTypes(typeNodes[0]))

    scopeNodes = dom.getElementsByTagNameNS(NS_D, "Scopes")
    if len(scopeNodes) > 0:
        env.getScopes().extend(getScopes(scopeNodes[0]))
    
    return env

def parseProbeMatchMessage(dom):
    env = SoapEnvelope()
    env.setAction(ACTION_PROBE_MATCH)

    env.setMessageId(dom.getElementsByTagNameNS(NS_A, "MessageID")[0].firstChild.data.strip())
    env.setRelatesTo(dom.getElementsByTagNameNS(NS_A, "RelatesTo")[0].firstChild.data.strip())
    env.setTo(dom.getElementsByTagNameNS(NS_A, "To")[0].firstChild.data.strip())

    appSeqNode = dom.getElementsByTagNameNS(NS_D, "AppSequence")[0]
    env.setInstanceId(appSeqNode.getAttribute("InstanceId"))
    env.setSequenceId(appSeqNode.getAttribute("SequenceId"))
    env.setMessageNumber(appSeqNode.getAttribute("MessageNumber"))

    pmNodes = dom.getElementsByTagNameNS(NS_D, "ProbeMatch")
    for node in pmNodes:
        epr = node.getElementsByTagNameNS(NS_A, "Address")[0].firstChild.data.strip()
        
        types = None
        typeNodes = node.getElementsByTagNameNS(NS_D, "Types")
        if len(typeNodes) > 0:
            types = getTypes(typeNodes[0])

        scopes = None
        scopeNodes = node.getElementsByTagNameNS(NS_D, "Scopes")
        if len(scopeNodes) > 0:
            scopes = getScopes(scopeNodes[0])
            
        xAddrs = None
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

    appSeqNode = dom.getElementsByTagNameNS(NS_D, "AppSequence")[0]
    env.setInstanceId(appSeqNode.getAttribute("InstanceId"))
    env.setSequenceId(appSeqNode.getAttribute("SequenceId"))
    env.setMessageNumber(appSeqNode.getAttribute("MessageNumber"))

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

    appSeqNode = dom.getElementsByTagNameNS(NS_D, "AppSequence")[0]
    env.setInstanceId(appSeqNode.getAttribute("InstanceId"))
    env.setSequenceId(appSeqNode.getAttribute("SequenceId"))
    env.setMessageNumber(appSeqNode.getAttribute("MessageNumber"))

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

    appSeqNode = dom.getElementsByTagNameNS(NS_D, "AppSequence")[0]
    env.setInstanceId(appSeqNode.getAttribute("InstanceId"))
    env.setSequenceId(appSeqNode.getAttribute("SequenceId"))
    env.setMessageNumber(appSeqNode.getAttribute("MessageNumber"))
    
    env.setEPR(dom.getElementsByTagNameNS(NS_A, "Address")[0].firstChild.data.strip())
    
    return env

def parseEnvelope(data):
    dom = minidom.parseString(data)    
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

def sendMessage(sock, addr, port, data):
    sock.sendto(data, (addr, port))

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

class MessageReceiverThread(threading.Thread):

    def __init__(self, sock, midMap, iidMap, observer):
        self.__sock = sock
        self.__midMap = midMap
        self.__iidMap = iidMap
        self.__observer = observer
        self.__stop = False
        threading.Thread.__init__(self)
        self.setDaemon(True)

    def run(self):
        while not self.__stop:
            val = readMessage(self.__sock)
            if val is None:
                time.sleep(0.01)
                continue
            (data, addr) = val

            env = parseEnvelope(data)

            mid = env.getMessageId()
            if self.__midMap.has_key(mid):
                continue
            else:
                self.__midMap[mid] = 0
            
            iid = env.getInstanceId()
            mid = env.getMessageId()
            if iid > 0:
                mnum = env.getMessageNumber()
                key = addr[0] + ":" + str(addr[1]) + ":" + str(iid)
                if mid is not None and len(mid) > 0:
                    key = key + ":" + mid
                if not self.__iidMap.has_key(key):
                    self.__iidMap[key] = iid
                else:
                    tmnum = self.__iidMap[key]
                    if mnum > tmnum:
                        self.__iidMap[key] = mnum
                    else:
                        continue

            self.__observer.envReceived(env, addr)
            
    def stop(self):
        self.__stop = True

class MessageSenderThread(threading.Thread):

    def __init__(self, sock, midMap, udpRepeat, udpMinDelay, udpMaxDelay, udpUpperDelay):
        self.__sock = sock
        self.__midMap = midMap
        self.__udpRepeat = udpRepeat
        self.__udpMinDelay = udpMinDelay
        self.__udpMaxDelay = udpMaxDelay
        self.__udpUpperDelay = udpUpperDelay
        self.__stop = False
        self.__queue = []
        threading.Thread.__init__(self)
        self.setDaemon(True)

    def getUdpRepeat(self):
        return self.__udpRepeat

    def setUdpRepeat(self, udpRepeat):
        self.__udpRepeat = udpRepeat

    def getUdpMinDelay(self):
        return self.__udpMinDelay

    def setUdpMinDelay(self, udpMinDelay):
        self.__udpMinDelay = udpMinDelay

    def getUdpMaxDelay(self):
        return self.__udpMaxDelay

    def setUdpMaxDelay(self, udpMaxDelay):
        self.__udpMaxDelay = udpMaxDelay

    def getUdpUpperDelay(self):
        return self.__udpUpperDelay

    def setUdpUpperDelay(self, udpUpperDelay):
        self.__udpUpperDelay = udpUpperDelay
        
    def addMessage(self, env, addr, port, initialDelay=0):
        msg = Message(env, addr, port, self.__udpRepeat, \
                      self.__udpMinDelay, self.__udpMaxDelay, self.__udpUpperDelay, initialDelay)
        self.__queue.append(msg)
        self.__midMap[env.getMessageId()] = 0

    def stop(self):
        self.__stop = True

    def run(self):
        while not self.__stop or len(self.__queue) > 0:
            if len(self.__queue) == 0:
                time.sleep(0.1)
                continue
            msg = self.__queue.pop(0)
            if msg.canSend():
                data = createMessage(msg.getEnv())

                sendMessage(self.__sock, msg.getAddr(), msg.getPort(), data)
                msg.refresh()
                if not (msg.isFinished()):
                    self.__queue.append(msg)
            else:
                self.__queue.append(msg)
                time.sleep(0.01)

class Message:

    def __init__(self, env, addr, port, udpRepeat, udpMinDelay, udpMaxDelay, udpUpperDelay, initialDelay=0):
        self.__env = env
        self.__addr = addr
        self.__port = port
        self.__udpRepeat = udpRepeat
        self.__udpUpperDelay = udpUpperDelay
        self.__t = (udpMinDelay + ((udpMaxDelay - udpMinDelay) * random.random())) / 2
        self.__nextTime = int(time.time() * 1000) + initialDelay

    def getEnv(self):
        return self.__env

    def getAddr(self):
        return self.__addr

    def getPort(self):
        return self.__port
        
    def isFinished(self):
        return self.__udpRepeat <= 0

    def canSend(self):
        ct = int(time.time() * 1000)
        return self.__nextTime < ct

    def refresh(self):
        self.__t = self.__t * 2
        if self.__t > self.__udpUpperDelay:
            self.__t = self.__udpUpperDelay
        self.__nextTime = int(time.time() * 1000) + self.__t
        self.__udpRepeat = self.__udpRepeat - 1

class Service:

    def __init__(self, types, scopes, xAddrs, epr, instanceId):
        self.__types = types
        self.__scopes = scopes
        self.__xAddrs = xAddrs
        self.__epr = epr
        self.__instanceId = instanceId
        self.__messageNumber = 0
        self.__metadataVersion = 1

    def getTypes(self):
        return self.__types

    def setTypes(self, types):
        self.__types = types

    def getScopes(self):
        return self.__scopes

    def setScopes(self, scopes):
        self.__scopes = scopes

    def getXAddrs(self):
        return self.__xAddrs

    def setXAddrs(self, xAddrs):
        self.__xAddrs = xAddrs

    def getEPR(self):
        return self.__epr

    def setEPR(self, epr):
        self.__epr = epr

    def getInstanceId(self):
        return self.__instanceId

    def setInstanceId(self, instanceId):
        self.__instanceId = instanceId

    def getMessageNumber(self):
        return self.__messageNumber

    def setMessageNumber(self, messageNumber):
        self.__messageNumber = messageNumber

    def getMetadataVersion(self):
        return self.__metadataVersion

    def setMetadataVersion(self, metadataVersion):
        self.__metadataVersion = metadataVersion

    def incrementMessageNumber(self):
        self.__messageNumber = self.__messageNumber + 1
        
class WSDiscovery:

    def __init__(self):
        self.__sockMultiOut = None
        self.__sockMultiIn = None
        self.__sockUniOut = None
        
        self.__multicastSenderThread = None
        self.__multicastReceiverThread = None
        self.__unicastSenderThread = None
        self.__unicastReceiverThread = None
        self.__serverStarted = False
        self.__remoteServices = {}
        self.__localServices = {}

        self.__dpActive = False
        self.__dpAddr = None
        self.__dpEPR = None

    def __addRemoteService(self, types, scopes, xAddrs, epr):
        service = Service(types, scopes, xAddrs, epr, 0)
        self.__remoteServices[epr] = service

    def __removeRemoteService(self, epr):
        if self.__remoteServices.has_key(epr):
            del self.__remoteServices[epr]

    def handleEnv(self, env, addr):        
        if (env.getAction() == ACTION_PROBE_MATCH):
            for match in env.getProbeResolveMatches():
                self.__addRemoteService(match.getTypes(), match.getScopes(), match.getXAddrs(), match.getEPR())
                if match.getXAddrs() is None or len(match.getXAddrs()) == 0:
                    self.__sendResolve(match.getEPR())
                    
        elif env.getAction() == ACTION_RESOLVE_MATCH:
            for match in env.getProbeResolveMatches():
                self.__addRemoteService(match.getTypes(), match.getScopes(), match.getXAddrs(), match.getEPR())

        elif env.getAction() == ACTION_PROBE:
            services = self.__filterServices(self.__localServices.values(), env.getTypes(), env.getScopes())
            self.__sendProbeMatch(services, env.getMessageId(), addr)

        elif env.getAction() == ACTION_RESOLVE:
            if self.__localServices.has_key(env.getEPR()):
                service = self.__localServices[env.getEPR()]
                self.__sendResolveMatch(service, env.getMessageId(), addr)

        elif env.getAction() == ACTION_HELLO:
            #check if it is from a discovery proxy
            rt = env.getRelationshipType()
            if rt is not None and rt.getLocalname() == "Suppression" and rt.getNamespace() == NS_D:
                xAddr = env.getXAddrs()[0]
                #only support 'soap.udp'
                if xAddr.startswith("soap.udp:"):
                    self.__dpActive = True
                    self.__dpAddr = extractSoapUdpAddressFromURI(URI(xAddr))
                    self.__dpEPR = env.getEPR()

            self.__addRemoteService(env.getTypes(), env.getScopes(), env.getXAddrs(), env.getEPR())

        elif env.getAction() == ACTION_BYE:
            #if the bye is from discovery proxy... revert back to multicasting
            if self.__dpActive and self.__dpEPR == env.getEPR():
                self.__dpActive = False
                self.__dpAddr = None
                self.__dpEPR = None
            
            self.__removeRemoteService(env.getEPR())

    def envReceived(self, env, addr):
        thread.start_new_thread(self.handleEnv, (env, addr))

    def __sendResolveMatch(self, service, relatesTo, addr):
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
        self.__unicastSenderThread.addMessage(env, addr[0], addr[1])

    def __sendProbeMatch(self, services, relatesTo, addr):
        env = SoapEnvelope()
        env.setAction(ACTION_PROBE_MATCH)
        env.setTo(ADDRESS_UNKNOWN)
        env.setMessageId(uuid.uuid4().get_urn())
        random.seed((int)(time.time() * 1000000))
        env.setInstanceId(str(random.randint(1, 0xFFFFFFF)))
        env.setMessageNumber("1")
        env.setRelatesTo(relatesTo)

        for service in services:
            env.getProbeResolveMatches().append(ProbeResolveMatch(service.getEPR(), \
                                                                  service.getTypes(), service.getScopes(), \
                                                                  service.getXAddrs(), str(service.getMetadataVersion())))

        self.__unicastSenderThread.addMessage(env, addr[0], addr[1], random.randint(0, APP_MAX_DELAY))

    def __sendProbe(self, types=None, scopes=None):
        env = SoapEnvelope()
        env.setAction(ACTION_PROBE)
        env.setTo(ADDRESS_ALL)
        env.setMessageId(uuid.uuid4().get_urn())
        env.setTypes(types)
        env.setScopes(scopes)

        if self.__dpActive:
            self.__unicastSenderThread.addMessage(env, self.__dpAddr[0], self.__dpAddr[1])
        else:
            self.__multicastSenderThread.addMessage(env, MULTICAST_IPV4_ADDRESS, MULTICAST_PORT)

    def __sendResolve(self, epr):
        env = SoapEnvelope()
        env.setAction(ACTION_RESOLVE)
        env.setTo(ADDRESS_ALL)
        env.setMessageId(uuid.uuid4().get_urn())
        env.setEPR(epr)

        if self.__dpActive:
            self.__unicastSenderThread.addMessage(env, self.__dpAddr[0], self.__dpAddr[1])
        else:
            self.__multicastSenderThread.addMessage(env, MULTICAST_IPV4_ADDRESS, MULTICAST_PORT)

    def __sendHello(self, service):
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

        self.__multicastSenderThread.addMessage(env, MULTICAST_IPV4_ADDRESS, MULTICAST_PORT, random.randint(0, APP_MAX_DELAY))

    def __sendBye(self, service):
        env = SoapEnvelope()
        env.setAction(ACTION_BYE)
        env.setTo(ADDRESS_ALL)
        env.setMessageId(uuid.uuid4().get_urn())
        env.setInstanceId(str(service.getInstanceId()))
        env.setMessageNumber(str(service.getMessageNumber()))
        env.setEPR(service.getEPR())

        service.incrementMessageNumber()
        self.__multicastSenderThread.addMessage(env, MULTICAST_IPV4_ADDRESS, MULTICAST_PORT)

    def start(self):
        'start the discovery server - should be called before using other functions'
        
        self.__startThreads()
        self.__serverStarted = True

    def stop(self):
        'cleans up and stops the discovery server'

        self.clearRemoteServices()
        self.clearLocalServices()

        self.__stopThreads()
        self.__serverStarted = False

    def __startThreads(self):
        if self.__multicastSenderThread is not None:
            return
        
        self.__sockMultiOut = createMulticastOutSocket()
        self.__sockMultiIn = createMulticastInSocket()
        self.__sockUniOut = createUnicastOutSocket()

        iidMap = {}
        midMap = {}

        self.__multicastSenderThread = MessageSenderThread(self.__sockMultiOut, midMap, \
                                MULTICAST_UDP_REPEAT, MULTICAST_UDP_MIN_DELAY, \
                                MULTICAST_UDP_MAX_DELAY, MULTICAST_UDP_UPPER_DELAY)
        self.__multicastSenderThread.start()

        self.__unicastSenderThread = MessageSenderThread(self.__sockUniOut, midMap, \
                                UNICAST_UDP_REPEAT, UNICAST_UDP_MIN_DELAY, \
                                UNICAST_UDP_MAX_DELAY, UNICAST_UDP_UPPER_DELAY)
        self.__unicastSenderThread.start()

        self.__multicastReceiverThread = MessageReceiverThread(self.__sockMultiIn, midMap, iidMap, self)
        self.__multicastReceiverThread.start()

        self.__unicastReceiverThread = MessageReceiverThread(self.__sockMultiOut, midMap, iidMap, self)
        self.__unicastReceiverThread.start()


    def __stopThreads(self):
        if self.__multicastSenderThread is None:
            return

        self.__unicastReceiverThread.stop()
        self.__unicastReceiverThread.join()
        
        self.__multicastReceiverThread.stop()
        self.__multicastReceiverThread.join()

        self.__unicastSenderThread.stop()
        self.__unicastSenderThread.join()
        
        self.__multicastSenderThread.stop()
        self.__multicastSenderThread.join()
        
        self.__sockMultiOut.close()
        self.__sockMultiIn.close()
        self.__sockUniOut.close()

        self.__sockMultiOut = None
        self.__sockMultiIn = None
        self.__sockUniOut = None
        
        self.__multicastSenderThread = None
        self.__multicastReceiverThread = None
        self.__unicastSenderThread = None
        self.__unicastReceiverThread = None

    def __isTypeInList(self, ttype, types):
        for entry in types:
            if matchType(ttype, entry):
                return True
            
        return False
    
    def __isScopeInList(self, scope, scopes):
        for entry in scopes:
            if matchScope(scope.getValue(), entry.getValue(), scope.getMatchBy()):
                return True
            
        return False

    def __filterServices(self, services, types, scopes):
        ret = []

        ok = True
        for service in services:
            ok = True
            if types is not None:
                for ttype in types:
                    if not self.__isTypeInList(ttype, service.getTypes()):
                        ok = False
                        break
            if ok and scopes is not None:
                for scope in scopes:
                    if not self.__isScopeInList(scope, service.getScopes()):
                        ok = False
                        break
            if ok:
                ret.append(service)
                
        return ret

    def clearRemoteServices(self):
        'clears remotely discovered services'
        
        self.__remoteServices.clear()

    def clearLocalServices(self):
        'send Bye messages for the services and remove them'
        
        for service in self.__localServices.values():
            self.__sendBye(service)

        self.__localServices.clear()

    def searchServices(self, types=None, scopes=None, timeout=3):
        'search for services given the TYPES and SCOPES in a given TIMEOUT'
        
        if not self.__serverStarted:
            raise Exception("Server not started")

        self.__sendProbe(types, scopes)
        
        time.sleep(timeout)

        return self.__filterServices(self.__remoteServices.values(), types, scopes)

    def publishService(self, types, scopes, xAddrs):
        'publish a service with the given TYPES, SCOPES and XAddrs (service addresses)'
        
        if not self.__serverStarted:
            raise Exception("Server not started")
        
        instanceId = (int) (time.time() * 1000000)
        epr = uuid.uuid4().get_urn()
        
        service = Service(types, scopes, xAddrs, epr, instanceId)
        self.__localServices[epr] = service
        self.__sendHello(service)
        
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
    
    xAddr = "localhost:8080/abc"
    wsd.publishService(types=[ttype], scopes=[scope2], xAddrs=[xAddr])
    
    #ret = wsd.searchServices(scopes=[scope1], timeout=10)
    ret = wsd.searchServices()
    
    for service in ret:
        print service.getEPR() + ":" + service.getXAddrs()[0]

    wsd.stop()
