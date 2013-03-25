# -*- coding: utf-8 -*-

from collections import OrderedDict

from pcreceiver import soap


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
