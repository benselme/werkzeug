# -*- coding: utf-8 -*-
"""
    werkzeug.testsuite.urls
    ~~~~~~~~~~~~~~~~~~~~~~~

    URL helper tests.

    :copyright: (c) 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""

import unittest
from io import BytesIO
import six
from werkzeug._internal import force_str

from werkzeug.testsuite import WerkzeugTestCase

from werkzeug.datastructures import OrderedMultiDict
from werkzeug import urls


class URLsTestCase(WerkzeugTestCase):

    def test_quoting(self):
        assert urls.url_quote(u'\xf6\xe4\xfc') == '%C3%B6%C3%A4%C3%BC'
        assert urls.url_unquote(urls.url_quote(u'#%="\xf6')) == u'#%="\xf6'
        assert urls.url_quote_plus('foo bar') == 'foo+bar'
        assert urls.url_unquote_plus('foo+bar') == 'foo bar'
        assert urls.url_encode({'a': None, 'b': 'foo bar'}) == 'b=foo+bar'
        assert urls.url_fix(u'http://de.wikipedia.org/wiki/Elf (Begriffsklärung)') == \
               'http://de.wikipedia.org/wiki/Elf%20%28Begriffskl%C3%A4rung%29'

    def test_url_decoding(self):
        x = urls.url_decode('foo=42&bar=23&uni=H%C3%A4nsel')
        assert x['foo'] == '42'
        assert x['bar'] == '23'
        assert x['uni'] == u'Hänsel'

        x = urls.url_decode('foo=42;bar=23;uni=H%C3%A4nsel', separator=';')
        assert x['foo'] == '42'
        assert x['bar'] == '23'
        assert x['uni'] == u'Hänsel'

        x = urls.url_decode('%C3%9Ch=H%C3%A4nsel', decode_keys=True)
        assert x[u'Üh'] == u'Hänsel'

    def test_streamed_url_decoding(self):
        item1 = b'a' * 100000
        item2 = b'b' * 400
        string = b'a=' + item1 + b'&b=' + item2 + b'&c=' + item2
        gen = urls.url_decode_stream(BytesIO(string), limit=len(string),
                                     return_iterator=True)
        self.assert_equal(six.next(gen), ('a', force_str(item1)))
        self.assert_equal(six.next(gen), ('b', force_str(item2)))
        self.assert_equal(six.next(gen), ('c', force_str(item2)))
        with self.assert_raises(StopIteration):
            six.next(gen)

    def test_url_encoding(self):
        assert urls.url_encode({'foo': 'bar 45'}) == 'foo=bar+45'
        d = {'foo': 1, 'bar': 23, 'blah': u'Hänsel'}
        assert urls.url_encode(d, sort=True) == 'bar=23&blah=H%C3%A4nsel&foo=1'
        assert urls.url_encode(d, sort=True, separator=';') == 'bar=23;blah=H%C3%A4nsel;foo=1'

    def test_sorted_url_encode(self):
        self.assertEqual(
            urls.url_encode({"a": 42, "b": 23, "1": 1, "2": 2}, sort=True),
            '1=1&2=2&a=42&b=23')
        assert urls.url_encode({'A': 1, 'a': 2, 'B': 3, 'b': 4}, sort=True,
                          key=lambda x: x[0].lower() + x[0]) == 'A=1&a=2&B=3&b=4'

    def test_streamed_url_encoding(self):
        out = BytesIO()
        urls.url_encode_stream({b'foo': b'bar 45'}, out, as_bytes=True)
        self.assert_equal(out.getvalue(), b'foo=bar+45')

        d = {b'foo': 1, b'bar': 23, b'blah': u'Hänsel'}
        out = BytesIO()
        urls.url_encode_stream(d, out, sort=True, as_bytes=True)
        self.assert_equal(out.getvalue(), b'bar=23&blah=H%C3%A4nsel&foo=1')
        out = BytesIO()
        urls.url_encode_stream(d, out, sort=True, separator=';', as_bytes=True)
        self.assert_equal(out.getvalue(), b'bar=23;blah=H%C3%A4nsel;foo=1')

        gen = urls.url_encode_stream(d, sort=True, as_bytes=True)
        self.assert_equal(six.next(gen), b'bar=23')
        self.assert_equal(six.next(gen), b'blah=H%C3%A4nsel')
        self.assert_equal(six.next(gen), b'foo=1')
        with self.assert_raises(StopIteration):
            six.next(gen)

    def test_url_fixing(self):
        x = urls.url_fix(u'http://de.wikipedia.org/wiki/Elf (Begriffskl\xe4rung)')
        assert x == 'http://de.wikipedia.org/wiki/Elf%20%28Begriffskl%C3%A4rung%29'

        x = urls.url_fix('http://example.com/?foo=%2f%2f')
        assert x == 'http://example.com/?foo=%2f%2f'

    def test_iri_support(self):
        with self.assert_raises(UnicodeError):
            urls.uri_to_iri(u'http://föö.com/')
        with self.assert_raises(UnicodeError):
            urls.iri_to_uri(b'http://f\x94\x94.com/')
        assert urls.uri_to_iri('http://xn--n3h.net/') == u'http://\u2603.net/'
        assert urls.uri_to_iri('http://%C3%BCser:p%C3%A4ssword@xn--n3h.net/p%C3%A5th') == \
            u'http://\xfcser:p\xe4ssword@\u2603.net/p\xe5th'
        assert urls.iri_to_uri(u'http://☃.net/') == 'http://xn--n3h.net/'
        assert urls.iri_to_uri(u'http://üser:pässword@☃.net/påth') == \
            'http://%C3%BCser:p%C3%A4ssword@xn--n3h.net/p%C3%A5th'
        self.assertEqual(urls.iri_to_uri(u'http://☃.net/?q=aع'),
                         'http://xn--n3h.net/?q=a%D8%B9')
        self.assertEqual(urls.iri_to_uri(u'http://☃.net/?q=a#bع'),
                         'http://xn--n3h.net/?q=a#b%D8%B9')

        self.assertEqual(
            urls.uri_to_iri('http://test.com/%3Fmeh?foo=%26%2F#anchor'),
            u'http://test.com/%3Fmeh?foo=%26%2F#anchor')

        # this should work as well, might break on 2.4 because of a broken
        # idna codec
        assert urls.uri_to_iri('/foo') == u'/foo'
        assert urls.iri_to_uri(u'/foo') == '/foo'

    def test_ordered_multidict_encoding(self):
        d = OrderedMultiDict()
        d.add('foo', 1)
        d.add('foo', 2)
        d.add('foo', 3)
        d.add('bar', 0)
        d.add('foo', 4)
        assert urls.url_encode(d) == 'foo=1&foo=2&foo=3&bar=0&foo=4'

    def test_href(self):
        x = urls.Href('http://www.example.com/')
        assert x('foo') == 'http://www.example.com/foo'
        assert x.foo('bar') == 'http://www.example.com/foo/bar'
        assert x.foo('bar', x=42) == 'http://www.example.com/foo/bar?x=42'
        assert x.foo('bar', class_=42) == 'http://www.example.com/foo/bar?class=42'
        assert x.foo('bar', {'class': 42}) == 'http://www.example.com/foo/bar?class=42'
        self.assert_raises(AttributeError, lambda: x.__blah__)

        x = urls.Href('blah')
        assert x.foo('bar') == 'blah/foo/bar'

        self.assert_raises(TypeError, x.foo, {"foo": 23}, x=42)

        x = urls.Href('')
        assert x('foo') == 'foo'

    def test_href_url_join(self):
        x = urls.Href('test')
        assert x('foo:bar') == 'test/foo:bar'
        assert x('http://example.com/') == 'test/http://example.com/'

    if 0:
        # stdlib bug? :(
        def test_href_past_root(self):
            base_href = urls.Href('http://www.blagga.com/1/2/3')
            assert base_href('../foo') == 'http://www.blagga.com/1/2/foo'
            assert base_href('../../foo') == 'http://www.blagga.com/1/foo'
            assert base_href('../../../foo') == 'http://www.blagga.com/foo'
            assert base_href('../../../../foo') == 'http://www.blagga.com/foo'
            assert base_href('../../../../../foo') == 'http://www.blagga.com/foo'
            assert base_href('../../../../../../foo') == 'http://www.blagga.com/foo'

    def test_url_unquote_plus_unicode(self):
        # was broken in 0.6
        assert urls.url_unquote_plus(u'\x6d') == u'\x6d'
        assert type(urls.url_unquote_plus(u'\x6d')) is six.text_type

    def test_quoting_of_local_urls(self):
        rv = urls.iri_to_uri(u'/foo\x8f')
        assert rv == '/foo%C2%8F'
        assert type(rv) is str


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(URLsTestCase))
    return suite
