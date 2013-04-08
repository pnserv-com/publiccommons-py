# -*- coding: utf-8 -*-

import os
import logging.config
from ConfigParser import SafeConfigParser

from pcreceiver import nckvs

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


def search_config():
    path = os.getenv('PCRECEIVER_CONFIG')
    if path and os.path.exists(path):
        return path

    for dir_ in (os.getcwd(), os.path.expanduser('~'), '/etc'):
        path = os.path.join(dir_, 'pcreceiver.ini')
        if os.path.exists(path):
            return path

    return None


class RequestLogger(object):
    def __init__(self, application, logger_name='request.body'):
        self.application = application
        self.log = logging.getLogger(logger_name)

    def __call__(self, environ, start_response):
        length = int(environ.get('CONTENT_LENGTH', '0'))
        body = StringIO(environ['wsgi.input'].read(length))
        self.log.info(body.getvalue())
        environ['wsgi.input'] = body
        return self.application(environ, start_response)


config = search_config()
logging.config.fileConfig(config)

parser = SafeConfigParser()
parser.read(config)
config = dict(parser.items('nckvs'))
nckvs.setup(**config)

from pcreceiver.soap import application
application = RequestLogger(application)

if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    server = make_server('127.0.0.1', 7789, application)
    print('listening to http://127.0.0.1:7789')
    print('wsdl is at: http://localhost:7789/?wsdl')
    server.serve_forever()
