# -*- coding: utf-8 -*-
"""
    werkzeug.testsuite.formparser
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Tests the form parsing facilities.

    :copyright: (c) 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""

from __future__ import with_statement

import unittest
from io import BytesIO
from os.path import join, dirname
import six
from werkzeug._internal import force_bytes

from werkzeug.testsuite import WerkzeugTestCase

from werkzeug import formparser
from werkzeug.test import create_environ, Client
from werkzeug.wrappers import Request, Response
from werkzeug.exceptions import RequestEntityTooLarge


@Request.application
def form_data_consumer(request):
    result_object = request.args['object']
    if result_object == 'text':
        return Response(repr(request.form['text']))
    f = request.files[result_object]
    return Response(b'\n'.join((
        force_bytes(repr(f.filename)),
        force_bytes(repr(f.name)),
        force_bytes(repr(f.content_type)),
        f.stream.read()
    )))


def get_contents(filename):
    f = open(filename, 'rb')
    try:
        return f.read()
    finally:
        f.close()


class FormParserTestCase(WerkzeugTestCase):

    def test_limiting(self):
        data = b'foo=Hello+World&bar=baz'
        req = Request.from_values(input_stream=BytesIO(data),
                                  content_length=len(data),
                                  content_type='application/x-www-form-urlencoded',
                                  method='POST')
        req.max_content_length = 400
        self.assert_equal(req.form['foo'], 'Hello World')

        req = Request.from_values(input_stream=BytesIO(data),
                                  content_length=len(data),
                                  content_type='application/x-www-form-urlencoded',
                                  method='POST')
        req.max_form_memory_size = 7
        self.assert_raises(RequestEntityTooLarge, lambda: req.form['foo'])

        req = Request.from_values(input_stream=BytesIO(data),
                                  content_length=len(data),
                                  content_type='application/x-www-form-urlencoded',
                                  method='POST')
        req.max_form_memory_size = 400
        self.assert_equal(req.form['foo'], 'Hello World')

        data = (b'--foo\r\nContent-Disposition: form-field; name=foo\r\n\r\n'
                b'Hello World\r\n'
                b'--foo\r\nContent-Disposition: form-field; name=bar\r\n\r\n'
                b'bar=baz\r\n--foo--')
        req = Request.from_values(input_stream=BytesIO(data),
                                  content_length=len(data),
                                  content_type='multipart/form-data; boundary=foo',
                                  method='POST')
        req.max_content_length = 4
        self.assert_raises(RequestEntityTooLarge, lambda: req.form['foo'])

        req = Request.from_values(input_stream=BytesIO(data),
                                  content_length=len(data),
                                  content_type='multipart/form-data; boundary=foo',
                                  method='POST')
        req.max_content_length = 400
        self.assert_equal(req.form['foo'], 'Hello World')

        req = Request.from_values(input_stream=BytesIO(data),
                                  content_length=len(data),
                                  content_type='multipart/form-data; boundary=foo',
                                  method='POST')
        req.max_form_memory_size = 7
        self.assert_raises(RequestEntityTooLarge, lambda: req.form['foo'])

        req = Request.from_values(input_stream=BytesIO(data),
                                  content_length=len(data),
                                  content_type='multipart/form-data; boundary=foo',
                                  method='POST')
        req.max_form_memory_size = 400
        self.assert_equal(req.form['foo'], 'Hello World')

    def test_parse_form_data_put_without_content(self):
        # A PUT without a Content-Type header returns empty data

        # Both rfc1945 and rfc2616 (1.0 and 1.1) say "Any HTTP/[1.0/1.1] message
        # containing an entity-body SHOULD include a Content-Type header field
        # defining the media type of that body."  In the case where either
        # headers are omitted, parse_form_data should still work.
        env = create_environ('/foo', 'http://example.org/', method='PUT')
        del env['CONTENT_TYPE']
        del env['CONTENT_LENGTH']

        stream, form, files = formparser.parse_form_data(env)
        self.assert_equal(stream.read(), b'')
        self.assert_equal(len(form), 0)
        self.assert_equal(len(files), 0)

    def test_parse_form_data_get_without_content(self):
        env = create_environ('/foo', 'http://example.org/', method='GET')
        del env['CONTENT_TYPE']
        del env['CONTENT_LENGTH']

        stream, form, files = formparser.parse_form_data(env)
        self.assert_equal(stream.read(), b'')
        self.assert_equal(len(form), 0)
        self.assert_equal(len(files), 0)

    def test_large_file(self):
        data = b'x' * (1024 * 600)
        req = Request.from_values(data={'foo': (BytesIO(data), 'test.txt')},
                                  method='POST')
        # make sure we have a real file here, because we expect to be
        # on the disk.  > 1024 * 500
        self.assertTrue(hasattr(req.files['foo'].stream, 'fileno'))
        req.files['foo'].stream.close()


class MultiPartTestCase(WerkzeugTestCase):

    def test_basic(self):
        resources = join(dirname(__file__), 'multipart')
        client = Client(form_data_consumer, Response)

        repository = [
            ('firefox3-2png1txt', '---------------------------186454651713519341951581030105', [
                (u'anchor.png', 'file1', 'image/png', 'file1.png'),
                (u'application_edit.png', 'file2', 'image/png', 'file2.png')
            ], u'example text'),
            ('firefox3-2pnglongtext', '---------------------------14904044739787191031754711748', [
                (u'accept.png', 'file1', 'image/png', 'file1.png'),
                (u'add.png', 'file2', 'image/png', 'file2.png')
            ], u'--long text\r\n--with boundary\r\n--lookalikes--'),
            ('opera8-2png1txt', '----------zEO9jQKmLc2Cq88c23Dx19', [
                (u'arrow_branch.png', 'file1', 'image/png', 'file1.png'),
                (u'award_star_bronze_1.png', 'file2', 'image/png', 'file2.png')
            ], u'blafasel öäü'),
            ('webkit3-2png1txt', '----WebKitFormBoundaryjdSFhcARk8fyGNy6', [
                (u'gtk-apply.png', 'file1', 'image/png', 'file1.png'),
                (u'gtk-no.png', 'file2', 'image/png', 'file2.png')
            ], u'this is another text with ümläüts'),
            ('ie6-2png1txt', '---------------------------7d91b03a20128', [
                (u'file1.png', 'file1', 'image/x-png', 'file1.png'),
                (u'file2.png', 'file2', 'image/x-png', 'file2.png')
            ], u'ie6 sucks :-/')
        ]

        for name, boundary, files, text in repository:
            folder = join(resources, name)
            data = get_contents(join(folder, 'request.txt'))
            for filename, field, content_type, fsname in files:
                response = client.post('/?object=' + field, data=data, content_type=
                'multipart/form-data; boundary="%s"' % boundary,
                                       content_length=len(data))
                lines = response.data.split(b'\n', 3)
                self.assert_equal(lines[0], force_bytes(repr(filename)))
                self.assert_equal(lines[1], force_bytes(repr(field)))
                self.assert_equal(lines[2], force_bytes(repr(content_type)))
                self.assert_equal(lines[3], get_contents(join(folder, fsname)))
            response = client.post('/?object=text', data=data, content_type=
            'multipart/form-data; boundary="%s"' % boundary,
                                   content_length=len(data))
            self.assert_equal(response.data, force_bytes(repr(text)))

    def test_ie7_unc_path(self):
        client = Client(form_data_consumer, Response)
        data_file = join(dirname(__file__), 'multipart', 'ie7_full_path_request.txt')
        data = get_contents(data_file)
        boundary = '---------------------------7da36d1b4a0164'
        response = client.post('/?object=cb_file_upload_multiple', data=data, content_type=
        'multipart/form-data; boundary="%s"' % boundary, content_length=len(data))
        lines = response.data.split(b'\n', 3)
        self.assertEqual(
            lines[0],
            force_bytes(repr(u'Sellersburg Town Council Meeting 02-22-2010doc.doc')))

    def test_end_of_file(self):
        # This test looks innocent but it was actually timeing out in
        # the Werkzeug 0.5 release version (#394)
        data = (
            b'--foo\r\n'
            b'Content-Disposition: form-data; name="test"; filename="test.txt"\r\n'
            b'Content-Type: text/plain\r\n\r\n'
            b'file contents and no end'
        )
        data = Request.from_values(input_stream=BytesIO(data),
                                   content_length=len(data),
                                   content_type='multipart/form-data; boundary=foo',
                                   method='POST')
        self.assertTrue(not data.files)
        self.assertTrue(not data.form)

    def test_broken(self):
        data = (
            b'--foo\r\n'
            b'Content-Disposition: form-data; name="test"; filename="test.txt"\r\n'
            b'Content-Transfer-Encoding: base64\r\n'
            b'Content-Type: text/plain\r\n\r\n'
            b'broken base 64'
            b'--foo--'
        )
        _, form, files = formparser.parse_form_data(create_environ(data=data,
                                                                   method='POST', content_type='multipart/form-data; boundary=foo'))
        self.assertTrue(not files)
        self.assertTrue(not form)

        self.assert_raises(ValueError, formparser.parse_form_data,
                           create_environ(data=data, method='POST',
                                          content_type='multipart/form-data; boundary=foo'),
                           silent=False)

    def test_file_no_content_type(self):
        data = (
            b'--foo\r\n'
            b'Content-Disposition: form-data; name="test"; filename="test.txt"\r\n\r\n'
            b'file contents\r\n--foo--'
        )
        data = Request.from_values(input_stream=BytesIO(data),
                                   content_length=len(data),
                                   content_type='multipart/form-data; boundary=foo',
                                   method='POST')
        self.assert_equal(data.files['test'].filename, 'test.txt')
        self.assert_equal(data.files['test'].read(), b'file contents')

    def test_extra_newline(self):
        # this test looks innocent but it was actually timeing out in
        # the Werkzeug 0.5 release version (#394)
        data = (
            b'\r\n\r\n--foo\r\n'
            b'Content-Disposition: form-data; name="foo"\r\n\r\n'
            b'a string\r\n'
            b'--foo--'
        )
        data = Request.from_values(input_stream=BytesIO(data),
                                   content_length=len(data),
                                   content_type='multipart/form-data; boundary=foo',
                                   method='POST')
        self.assertTrue(not data.files)
        self.assert_equal(data.form['foo'], 'a string')

    def test_headers(self):
        data = (b'--foo\r\n'
                b'Content-Disposition: form-data; name="foo"; filename="foo.txt"\r\n'
                b'X-Custom-Header: blah\r\n'
                b'Content-Type: text/plain; charset=utf-8\r\n\r\n'
                b'file contents, just the contents\r\n'
                b'--foo--')
        req = Request.from_values(input_stream=BytesIO(data),
                                  content_length=len(data),
                                  content_type='multipart/form-data; boundary=foo',
                                  method='POST')
        foo = req.files['foo']
        self.assert_equal(foo.mimetype, 'text/plain')
        self.assert_equal(foo.mimetype_params, {'charset': 'utf-8'})
        self.assert_equal(foo.headers['content-type'], foo.content_type)
        self.assert_equal(foo.content_type, 'text/plain; charset=utf-8')
        self.assert_equal(foo.headers['x-custom-header'], 'blah')

    def test_nonstandard_line_endings(self):
        for nl in b'\n', b'\r', b'\r\n':
            data = nl.join((
                b'--foo',
                b'Content-Disposition: form-data; name=foo',
                b'',
                b'this is just bar',
                b'--foo',
                b'Content-Disposition: form-data; name=bar',
                b'',
                b'blafasel',
                b'--foo--'
            ))
            req = Request.from_values(input_stream=BytesIO(data),
                                      content_length=len(data),
                                      content_type='multipart/form-data; '
                                                   'boundary=foo', method='POST')
            self.assert_equal(req.form['foo'], 'this is just bar')
            self.assert_equal(req.form['bar'], 'blafasel')

    def test_failures(self):
        def parse_multipart(stream, boundary, content_length):
            parser = formparser.MultiPartParser(content_length)
            return parser.parse(stream, boundary, content_length)
        self.assert_raises(ValueError, parse_multipart, BytesIO(), '', 0)
        self.assert_raises(ValueError, parse_multipart, BytesIO(), 'broken  ', 0)

        data = b'--foo\r\n\r\nHello World\r\n--foo--'
        self.assert_raises(ValueError, parse_multipart, BytesIO(data), 'foo', len(data))

        data = b'--foo\r\nContent-Disposition: form-field; name=foo\r\n' \
               b'Content-Transfer-Encoding: base64\r\n\r\nHello World\r\n--foo--'
        self.assert_raises(ValueError, parse_multipart, BytesIO(data), 'foo', len(data))

        data = b'--foo\r\nContent-Disposition: form-field; name=foo\r\n\r\nHello World\r\n'
        self.assert_raises(ValueError, parse_multipart, BytesIO(data), 'foo', len(data))

        x = formparser.parse_multipart_headers([b'foo: bar\r\n', b' x test\r\n'])
        self.assert_equal(x['foo'], 'bar\n x test')
        self.assert_raises(ValueError, formparser.parse_multipart_headers,
                           [b'foo: bar\r\n', b' x test'])

    def test_bad_newline_bad_newline_assumption(self):
        class ISORequest(Request):
            charset = 'latin1'
        contents = b'U2vlbmUgbORu'
        data = b'--foo\r\nContent-Disposition: form-data; name="test"\r\n' \
               b'Content-Transfer-Encoding: base64\r\n\r\n' + \
               contents + b'\r\n--foo--'
        req = ISORequest.from_values(input_stream=BytesIO(data),
                                     content_length=len(data),
                                     content_type='multipart/form-data; boundary=foo',
                                     method='POST')
        self.assert_equal(req.form['test'], u'Sk\xe5ne l\xe4n')


class InternalFunctionsTestCase(WerkzeugTestCase):

    def test_line_parser(self):
        self.assertEqual(formparser._line_parse(b'foo'), (b'foo', False))
        self.assertEqual(formparser._line_parse(b'foo\r\n'), (b'foo', True))
        self.assertEqual(formparser._line_parse(b'foo\r'), (b'foo', True))
        self.assertEqual(formparser._line_parse(b'foo\n'), (b'foo', True))

    def test_find_terminator(self):
        lineiter = iter('\n\n\nfoo\nbar\nbaz'.splitlines(True))
        find_terminator = formparser.MultiPartParser()._find_terminator
        line = find_terminator(lineiter)
        assert line == 'foo'
        assert list(lineiter) == ['bar\n', 'baz']
        assert find_terminator([]) == ''
        assert find_terminator(['']) == ''


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(FormParserTestCase))
    suite.addTest(unittest.makeSuite(MultiPartTestCase))
    suite.addTest(unittest.makeSuite(InternalFunctionsTestCase))
    return suite
