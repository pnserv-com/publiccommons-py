# -*- coding: utf-8 -*-

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
        return PublishResponse(response=ProcessResponse(code=0))


def parse(elem):
    d = Message()
    for el in elem:
        tag = el.tag.split('}')[-1]
        d[tag] = parse(el) if len(el) > 0 else el.text

    return d


class Message(dict):
    def __getattr__(self, key):
        if key in self:
            return self[key]
        raise AttributeError(key)

    def find(self, key):
        if key in self:
            return self[key]

        for v in (x for x in self.values() if isinstance(x, Message)):
            return v.find(key)

        return None


application = wsgi_soap_application([MQService], TARGET_NAMESPACE)

if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    server = make_server('127.0.0.1', 7789, application)
    print('listening to http://127.0.0.1:7789')
    print('wsdl is at: http://localhost:7789/?wsdl')
    server.serve_forever()
