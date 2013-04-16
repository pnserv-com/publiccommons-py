# -*- coding: utf-8 -*-

import os
os.environ['PUBLICCOMMONS_CONFIG'] = 'publiccommons.dev.ini'

from mock import patch
from webtest import TestApp

from publiccommons.wsgi import application

data_dir = os.path.join(os.path.dirname(__file__), 'data')


@patch('nckvsclient.KVSClient.set')
@patch('nckvsclient.KVSClient.search', return_value={'datalist': []})
def test_multibyte_data(search, set_):
    with open(os.path.join(data_dir, 'soap1.xml')) as f:
        xml = f.read()

    header = {'Content-Type': 'application/soap+xml;charset=UTF-8'}
    app = TestApp(application)
    res = app.post('/', xml, header)

    assert set_.call_count == 1
    assert res.status_int == 200
    assert res.content_type == 'text/xml'
