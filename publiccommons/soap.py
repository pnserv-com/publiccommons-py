# -*- coding: utf-8 -*-

import re
import json
import logging

import lxml.etree
from spyne.decorator import srpc
from spyne.service import ServiceBase
from spyne.model.primitive import Integer, AnyXml
from spyne.model.complex import ComplexModel
from spyne.application import Application
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication

TARGET_NAMESPACE = 'http://soap.publiccommons.ne.jp/'
NS_MAP = {
    'edxlde': 'urn:oasis:names:tc:emergency:EDXL:DE:1.0',
    'commons': 'http://xml.publiccommons.ne.jp/xml/edxl/',
    'pcx_ib': 'http://xml.publiccommons.ne.jp/pcxml1/informationBasis3/',
    'pcx_cns_i3': 'http://xml.publiccommons.ne.jp/pcxml1/informationBasis4/'
}

log = logging.getLogger(__name__)
nckvs = None


class ProcessResponse(ComplexModel):
    __namespace__ = TARGET_NAMESPACE
    code = Integer
    result = AnyXml


class PublishResponse(ComplexModel):
    __namespace__ = TARGET_NAMESPACE
    response = ProcessResponse


class MQService(ServiceBase):
    @srpc(AnyXml, _returns=PublishResponse)
    def publish(message):
        try:
            return _publish(message)
        except Exception as e:
            log.exception(e)
            raise


def _publish(message):
    def exp(ns, name):
        return '{{{0}}}{1}'.format(NS_MAP[ns], name)

    root = parse(message)
    content = root[exp('commons', 'contentObject')]
    document = content.find(exp('edxlde', 'embeddedXMLContent'))
    if document.find(exp('pcx_ib', 'Title')):
        ns_ib = 'pcx_ib'
    else:
        ns_ib = 'pcx_cns_i3'

    param = {
        'status': root[exp('edxlde', 'distributionStatus')],
        'document_id': content[exp('commons', 'documentID')],
        'revision': content[exp('commons', 'documentRevision')],
        'category': content[exp('commons', 'category')],
        'area_code': root[exp('commons', 'targetArea')][exp('commons', 'jisX0402')],
        'title': document.find(exp(ns_ib, 'Title')),
        'summary': document.find(exp(ns_ib, 'Headline'))[exp(ns_ib, 'Text')],
        'raw': root.shorten()
    }

    upsert(param)
    return PublishResponse(response=ProcessResponse(code=0))


class XMLDict(dict):
    def __init__(self, ns=None):
        super(XMLDict, self).__init__()
        self.ns = ns or {}

    def find(self, key):
        if key in self:
            return self[key]

        for v in (x for x in self.values() if isinstance(x, XMLDict)):
            r = v.find(key)
            if r:
                return r

        return None

    def shorten(self):
        elem = ShortXMLDict(self.ns)
        for key, value in self.iteritems():
            if isinstance(value, XMLDict):
                value = value.shorten()
            elem[key] = value

        return elem

    def encode(self, encoding):
        elem = self.__class__(self.ns)
        for key, value in self.items():
            key = self._encode(key, encoding)
            if isinstance(value, XMLDict):
                elem[key] = value.encode(encoding)
            else:
                elem[key] = self._encode(value, encoding)

        return elem

    def _encode(self, s, encoding):
        if isinstance(s, unicode):
            return s.encode(encoding)
        return s


class ShortXMLDict(XMLDict):
    namespace_re = re.compile(r'{([^}]+)}(.+)')

    def __init__(self, ns=None):
        super(ShortXMLDict, self).__init__(ns)
        self.rns = {v: k for k, v in self.ns.items()}
        if None in self.ns:
            self.rns[self.ns[None]] = None

    def __setitem__(self, key, value):
        if isinstance(value, XMLDict):
            # keys must evalueted in child element's namespaces
            # because a default namespace is also applied on a declared tag
            key = value.resolve(key)
        else:
            key = self.resolve(key)
        super(XMLDict, self).__setitem__(key, value)

    def resolve(self, name):
        m = self.namespace_re.match(name)
        if not m:
            return name

        alias = self.rns.get(m.group(1))
        if alias:
            return '{}:{}'.format(alias, m.group(2))
        else:
            return m.group(2)


def parse(elem):
    d = XMLDict(elem.nsmap)
    for el in (x for x in elem if not isinstance(x, lxml.etree._Comment)):
        d[el.tag] = parse(el) if len(el) > 0 else el.text

    return d


def upsert(data):
    data = dict(data)
    matches = nckvs.search([{
        'key': 'document_id', 'value': data['document_id'],
        'pattern': 'cmp'
    }])['datalist']

    document_key = '{}.{}'.format(data['document_id'], data['revision'])
    if not matches:
        data['id'] = '-1'
        log.info('new document: ' + document_key)
    elif int(matches[0]['revision']) >= int(data['revision']):
        log.info('same document exists: ' + document_key)
        return
    else:
        data['id'] = matches[0]['id']
        log.info('update document: ' + document_key)

    return nckvs.set([data])


def get_app(kvsclient):
    import sys
    setattr(sys.modules[__name__], 'nckvs', kvsclient)

    application = Application([MQService], TARGET_NAMESPACE,
                              in_protocol=Soap11(validator='lxml'),
                              out_protocol=Soap11())

    # set block_length same as max_content_length
    # because splitting inappropriate position causes UnicodeDecodeError
    return WsgiApplication(application,
                           max_content_length=2 * 1024 * 1024,
                           block_length=2 * 1024 * 1024)
