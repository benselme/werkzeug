# -*- coding: utf-8 -*-
"""
    werkzeug.testsuite.serving
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    Added serving tests.

    :copyright: (c) 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import sys
import time
import urllib
from six.moves import http_client as httplib
import unittest
from functools import update_wrapper
import six

from werkzeug._internal import force_bytes
from werkzeug.testsuite import WerkzeugTestCase
from werkzeug import __version__ as version, serving
from werkzeug.testapp import test_app
from threading import Thread

try:
    from urllib.request import urlopen
    from urllib.error import HTTPError
except ImportError:
    from urllib2 import urlopen, HTTPError


real_make_server = serving.make_server


def silencestderr(f):
    def new_func(*args, **kwargs):
        old_stderr = sys.stderr
        sys.stderr = six.StringIO()
        try:
            return f(*args, **kwargs)
        finally:
            sys.stderr = old_stderr
    return update_wrapper(new_func, f)


def run_dev_server(application):
    servers = []
    def tracking_make_server(*args, **kwargs):
        srv = real_make_server(*args, **kwargs)
        servers.append(srv)
        return srv
    serving.make_server = tracking_make_server
    try:
        t = Thread(target=serving.run_simple, args=('localhost', 0, application))
        t.setDaemon(True)
        t.start()
        time.sleep(0.25)
    finally:
        serving.make_server = real_make_server
    if not servers:
        return None, None
    server ,= servers
    ip, port = server.socket.getsockname()[:2]
    if ':' in ip:
        ip = '[%s]' % ip
    return server, '%s:%d'  % (ip, port)


class ServingTestCase(WerkzeugTestCase):

    @silencestderr
    def test_serving(self):
        server, addr = run_dev_server(test_app)
        rv = urlopen('http://%s/?foo=bar&baz=blah' % addr).read()
        self.assertIn(b'WSGI Information', rv)
        self.assertIn(b'foo=bar&amp;baz=blah', rv)
        self.assertIn(force_bytes('Werkzeug/{}'.format(version)), rv)

    @silencestderr
    def test_broken_app(self):
        def broken_app(environ, start_response):
            1/0
        server, addr = run_dev_server(broken_app)
        with self.assertRaises(HTTPError) as cm:
            rv = urlopen('http://%s/?foo=bar&baz=blah' % addr).read()
        self.assertEqual(cm.exception.code, 500)

    @silencestderr
    def test_absolute_requests(self):
        def asserting_app(environ, start_response):
            assert environ['HTTP_HOST'] == 'surelynotexisting.example.com:1337'
            assert environ['PATH_INFO'] == '/index.htm'
            assert environ['SERVER_PORT'] == addr.split(':')[1]
            start_response('200 OK', [('Content-Type', 'text/html')])
            return 'YES'

        server, addr = run_dev_server(asserting_app)
        conn = httplib.HTTPConnection(addr)
        conn.request('GET', 'http://surelynotexisting.example.com:1337/index.htm')
        res = conn.getresponse()
        self.assertEqual(res.read(), b'YES')


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ServingTestCase))
    return suite
