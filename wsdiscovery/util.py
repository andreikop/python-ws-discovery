"""Various utilities used by different parts of the package."""

import io
import string
import random
import netifaces
from xml.dom import minidom
from .scope import Scope
from .uri import URI
from .namespaces import NS_ADDRESSING, NS_DISCOVERY, NS_SOAPENV
from .qname import QName


def createSkelSoapMessage(soapAction):
    doc = minidom.Document()

    envEl = doc.createElementNS(NS_SOAPENV, "s:Envelope")

    envEl.setAttribute("xmlns:a", NS_ADDRESSING)  # minidom does not insert this automatically
    envEl.setAttribute("xmlns:d", NS_DISCOVERY)
    envEl.setAttribute("xmlns:s", NS_SOAPENV)

    doc.appendChild(envEl)

    headerEl = doc.createElementNS(NS_SOAPENV, "s:Header")
    envEl.appendChild(headerEl)

    addElementWithText(doc, headerEl, "a:Action", NS_ADDRESSING, soapAction)

    bodyEl = doc.createElementNS(NS_SOAPENV, "s:Body")
    envEl.appendChild(bodyEl)

    return doc


def addElementWithText(doc, parent, name, ns, value):
    el = doc.createElementNS(ns, name)
    text = doc.createTextNode(value)
    el.appendChild(text)
    parent.appendChild(el)


def addEPR(doc, node, epr):
    eprEl = doc.createElementNS(NS_ADDRESSING, "a:EndpointReference")
    addElementWithText(doc, eprEl, "a:Address", NS_ADDRESSING, epr)
    node.appendChild(eprEl)


def addScopes(doc, node, scopes):
    if scopes is not None and len(scopes) > 0:
        addElementWithText(doc, node, "d:Scopes", NS_DISCOVERY, " ".join([x.getQuotedValue() for x in scopes]))
        if scopes[0].getMatchBy() is not None and len(scopes[0].getMatchBy()) > 0:
            node.getElementsByTagNameNS(NS_DISCOVERY, "Scopes")[0].setAttribute("MatchBy", scopes[0].getMatchBy())


def addTypes(doc, node, types):
    if types is not None and len(types) > 0:
        envEl = getEnvEl(doc)
        typeList = []
        prefixMap = {}
        for type in types:
            ns = type.getNamespace()
            localname = type.getLocalname()
            if type.getNamespacePrefix() is None:
                if prefixMap.get(ns) == None:
                    prefix = getRandomStr()
                    prefixMap[ns] = prefix
                else:
                    prefix = prefixMap.get(ns)
            else:
                prefix = type.getNamespacePrefix()
            addNSAttrToEl(envEl, ns, prefix)
            typeList.append(prefix + ":" + localname)
        addElementWithText(doc, node, "d:Types", NS_DISCOVERY, " ".join(typeList))


def addXAddrs(doc, node, xAddrs):
    if xAddrs is not len(xAddrs) > 0:
        addElementWithText(doc, node, "d:XAddrs", NS_DISCOVERY, " ".join([x for x in xAddrs]))


def getDocAsString(doc):
    outStr = None
    stream = io.StringIO(outStr)
    stream.write(doc.toprettyxml())
    return stream.getvalue()


def getBodyEl(doc):
    return doc.getElementsByTagNameNS(NS_SOAPENV, "Body")[0]


def getHeaderEl(doc):
    return doc.getElementsByTagNameNS(NS_SOAPENV, "Header")[0]


def getEnvEl(doc):
    return doc.getElementsByTagNameNS(NS_SOAPENV, "Envelope")[0]


def addNSAttrToEl(el, ns, prefix):
    el.setAttribute("xmlns:" + prefix, ns)


def _parseAppSequence(dom, env):
    nodes = dom.getElementsByTagNameNS(NS_DISCOVERY, "AppSequence")
    if nodes:
        appSeqNode = nodes[0]
        env.setInstanceId(appSeqNode.getAttribute("InstanceId"))
        env.setSequenceId(appSeqNode.getAttribute("SequenceId"))
        env.setMessageNumber(appSeqNode.getAttribute("MessageNumber"))


def _parseSpaceSeparatedList(node):
    if node.childNodes:
        return [item.replace('%20', ' ') \
            for item in node.childNodes[0].data.split()]
    else:
        return []


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


def getXAddrs(xAddrsNode):
    return _parseSpaceSeparatedList(xAddrsNode)


def getTypes(typeNode):
    return [getQNameFromValue(item, typeNode) \
                for item in _parseSpaceSeparatedList(typeNode)]


def getScopes(scopeNode):
    matchBy = scopeNode.getAttribute("MatchBy")
    return [Scope(item, matchBy) \
                for item in _parseSpaceSeparatedList(scopeNode)]


def matchScope(src, target, matchBy):

    MATCH_BY_LDAP = "http://schemas.xmlsoap.org/ws/2005/04/discovery/ldap"
    MATCH_BY_URI = "http://schemas.xmlsoap.org/ws/2005/04/discovery/rfc2396"
    MATCH_BY_UUID = "http://schemas.xmlsoap.org/ws/2005/04/discovery/uuid"
    MATCH_BY_STRCMP = "http://schemas.xmlsoap.org/ws/2005/04/discovery/strcmp0"

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


def isTypeInList(ttype, types):
    for entry in types:
        if ttype.getFullname() == entry.getFullname():
            return True
    return False


def isScopeInList(scope, scopes):
    for entry in scopes:
        if matchScope(scope.getValue(), entry.getValue(), scope.getMatchBy()):
            return True
    return False


def matchesFilter(service, types, scopes):
    if types is not None:
        for ttype in types:
            if not isTypeInList(ttype, service.getTypes()):
                return False
    if scopes is not None:
        for scope in scopes:
            if not isScopeInList(scope, service.getScopes()):
                return False
    return True


def filterServices(services, types, scopes):
    return [service for service in services if matchesFilter(service, types, scopes)]


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
    prefix = None
    if len(vals) == 1:
        localName = vals[0]
        ns = getDefaultNamespace(node)
    else:
        localName = vals[1]
        prefix = vals[0]
        ns = getNamespaceValue(node, prefix)
    return QName(ns, localName, prefix)


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


def getRandomStr():
    return "".join([random.choice(string.ascii_letters) for x in range(10)])


def showEnv(env):
    print("-----------------------------")
    print("Action: %s" % env.getAction())
    print("MessageId: %s" % env.getMessageId())
    print("InstanceId: %s" % env.getInstanceId())
    print("MessageNumber: %s" % env.getMessageNumber())
    print("Reply To: %s" % env.getReplyTo())
    print("To: %s" % env.getTo())
    print("RelatesTo: %s" % env.getRelatesTo())
    print("Relationship Type: %s" % env.getRelationshipType())
    print("Types: %s" % env.getTypes())
    print("Scopes: %s" % env.getScopes())
    print("EPR: %s" % env.getEPR())
    print("Metadata Version: %s" % env.getMetadataVersion())
    print("Probe Matches: %s" % env.getProbeResolveMatches())
    print("-----------------------------")

