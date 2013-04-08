# -*- coding: utf-8 -*-

import re
import json
import logging

import lxml.etree
from spyne.decorator import srpc
from spyne.service import ServiceBase
from spyne.model.primitive import Integer, AnyXml
from spyne.model.complex import ComplexModel
from spyne.util.simple import wsgi_soap_application

from pcreceiver import nckvs

TARGET_NAMESPACE = 'http://soap.publiccommons.ne.jp/'

log = logging.getLogger(__name__)


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
    root = parse(message)
    content = root['commons:contentObject']
    document = content.find('edxlde:embeddedXMLContent')
    ns = 'pcx_ib' if document.find('pcx_ib:Title') else 'pcx_cns_i3'
    param = {
        'status': root['edxlde:distributionStatus'],
        'document_id': content['commons:documentID'],
        'revision': content['commons:documentRevision'],
        'category': content['commons:category'],
        'area_code': root['commons:targetArea']['commons:jisX0402'],
        'title': document.find(ns + ':Title'),
        'summary': document.find(ns + ':Headline')[ns + ':Text'],
        'raw': json.dumps(root, ensure_ascii=False)
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
    d = ShortXMLDict(elem.nsmap)
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


application = wsgi_soap_application([MQService], TARGET_NAMESPACE)
