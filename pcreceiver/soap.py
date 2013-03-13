# -*- coding: utf-8 -*-

import re

import lxml.etree
from spyne.decorator import srpc
from spyne.service import ServiceBase
from spyne.model.primitive import Integer, AnyXml
from spyne.model.complex import ComplexModel
from spyne.util.simple import wsgi_soap_application

TARGET_NAMESPACE = 'http://soap.publiccommons.ne.jp/'


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
        with open('recv.xml', 'w') as f:
            f.write(lxml.etree.tostring(message))
        result = parse(message)
        print(result)
        print(result.find('edxlde:distributionID'))
        return PublishResponse(response=ProcessResponse(code=0))


class XMLDict(dict):
    namespace_re = re.compile(r'{([^}]+)}(.+)')

    def __init__(self, ns=None):
        super(XMLDict, self).__init__()
        self.ns = ns or {}
        self.rns = {v: k for k, v in self.ns.items()}

    def __setitem__(self, key, value):
        m = XMLDict.namespace_re.match(key)
        if m:
            alias = self.rns.get(m.group(1))
            if alias:
                key = '{}:{}'.format(alias, m.group(2))
            else:
                key = m.group(2)

        super(XMLDict, self).__setitem__(key, value)

    def find(self, key):
        if key in self:
            return self[key]

        for v in (x for x in self.values() if isinstance(x, XMLDict)):
            r = v.find(key)
            if r:
                return r

        return None


def parse(elem):
    d = XMLDict(elem.nsmap)
    for el in elem:
        d[el.tag] = parse(el) if len(el) > 0 else el.text

    return d


application = wsgi_soap_application([MQService], TARGET_NAMESPACE)

if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    server = make_server('127.0.0.1', 7789, application)
    print('listening to http://127.0.0.1:7789')
    print('wsdl is at: http://localhost:7789/?wsdl')
    server.serve_forever()
