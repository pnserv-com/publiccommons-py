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
        print lxml.etree.tostring(message)
        return PublishResponse(response=ProcessResponse(code=0))


application = wsgi_soap_application([MQService], TARGET_NAMESPACE)

if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    server = make_server('127.0.0.1', 7789, application)
    print('listening to http://127.0.0.1:7789')
    print('wsdl is at: http://localhost:7789/?wsdl')
    server.serve_forever()
