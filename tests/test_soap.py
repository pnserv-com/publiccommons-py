# -*- coding: utf-8 -*-

import os
import json
from collections import OrderedDict

import lxml.etree
from mock import patch, call

from pcreceiver import soap


def load_xml(filename):
    xml = os.path.join(os.path.dirname(__file__), 'data', filename)
    return lxml.etree.parse(xml).getroot()


def pytest_funcarg__xmldict(request):
    return {
        'edxlde:distributionID': '5eef9d6a-608f-4e7a-a9f7-2fa941d1abe2',
        'edxlde:dateTimeSent': '2010-11-30T14:59:00+09:00',
        'edxlde:distributionStatus': 'Actual',
        'commons:targetArea': {
            'commons:jisX0402': '282103'
        },
        'commons:contentObject': {
            'edxlde:xmlContent': {
                'edxlde:embeddedXMLContent': {
                    'Report': {
                        'pcx_ib:Head': {
                            'pcx_ib:Title': u'加古川市: 避難勧告・指示情報　発令',
                            'commons:documentID': '7e573043-fc3c-4a6b-bdb8-a9608233b0af',
                            'pcx_ib:Headline': {
                                'pcx_ib:Text': u'平成22年11月30日、A地区の土砂災害現場において避難勧告を行うこととしている基準雨量を超えたことによるもの（サンプル）'
                            }
                        }
                    }
                }
            },
            'commons:documentRevision': '1',
            'commons:documentID': '7e573043-fc3c-4a6b-bdb8-a9608233b0af',
            'commons:category': 'EvacuationOrder'
        }
    }



class TestXMLDict(object):
    nsmap = {
        'ns1': 'http://example.com/ns1',
        'ns2': 'http://example.com/ns2'
    }

    def test_init(self):
        d = soap.XMLDict(TestXMLDict.nsmap)
        assert d.ns == TestXMLDict.nsmap
        assert d.rns == {
        'http://example.com/ns1': 'ns1',
        'http://example.com/ns2': 'ns2'
    }

    def test_setitem(self):
        d = soap.XMLDict(TestXMLDict.nsmap)
        d['{http://example.com/ns1}foo'] = 1
        d['{http://example.com/ns2}foo'] = 2
        d['{http://example.com/ns3}foo'] = 3
        assert d['ns1:foo'] == 1
        assert d['ns2:foo'] == 2
        assert d['foo'] == 3

    def test_find(self):
        d = soap.XMLDict()
        d['foo'] = 1
        d['nest'] = soap.XMLDict()
        d['nest']['bar'] = 2
        d['nest2'] = soap.XMLDict()
        d['nest2']['baz'] = 3
        assert d.find('foo') == 1
        assert d.find('bar') == 2
        assert d.find('baz') == 3
        assert d.find('nothing') is None

    def test_default_ns(self):
        nsmap = OrderedDict({None: 'http://example.com/ns1'})
        nsmap.update(TestXMLDict.nsmap)

        d = soap.XMLDict(nsmap)
        d['{http://example.com/ns1}foo'] = 1
        assert d['foo'] == 1

        del nsmap[None]
        nsmap[None] = 'http://example.com/ns1'

        d = soap.XMLDict(nsmap)
        d['{http://example.com/ns1}foo'] = 1
        assert d['foo'] == 1

    def test_nested_default_ns(self):
        d1 = soap.XMLDict(TestXMLDict.nsmap)
        d2 = soap.XMLDict({'http://example.com/ns1': None})
        d2['{http://example.com/ns1}text'] = 'nested'
        d1['{http://example.com/ns1}child'] = d2
        assert d1['child']['text'] == 'nested'


def test_parse(xmldict):
    assert soap.parse(load_xml('sample1.xml')) == xmldict
    assert soap.parse(load_xml('sample2.xml')) == xmldict


class TestMQService(object):
    @patch('pcreceiver.soap.upsert')
    def test_publish(self, upsert, xmldict):
        message = load_xml('sample1.xml')
        svc = soap.MQService()
        res = svc.publish(message)
        assert res.response.code == 0

        # inspect upsert calls
        args, _ = upsert.call_args
        data = args[0]
        raw = data.pop('raw')
        assert data == {
            'status': 'Actual',
            'document_id': '7e573043-fc3c-4a6b-bdb8-a9608233b0af',
            'revision': '1',
            'category': 'EvacuationOrder',
            'area_code': '282103',
            'title': u'加古川市: 避難勧告・指示情報　発令',
            'summary': u'平成22年11月30日、A地区の土砂災害現場において避難勧告を行うこととしている基準雨量を超えたことによるもの（サンプル）'
        }
        assert json.loads(raw) == xmldict
