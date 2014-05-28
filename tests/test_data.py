# See file COPYING distributed with dpf for copyright and license.

import uuid
import httplib
import json
from . import start_data_server, stop_server

test_vars = {}

def setup():
    po, fo_out, fo_err = start_data_server()
    test_vars['po'] = po
    test_vars['fo_out'] = fo_out
    test_vars['fo_err'] = fo_err
    return

def teardown():
    stop_server(test_vars['po'], test_vars['fo_out'], test_vars['fo_err'])
    return

class BaseDataTest:

    n_connections = 0

    def setUp(self):
        """set up each test"""
        self.connections = []
        self.next_connection = 0
        for i in xrange(self.n_connections):
            self.connections.append(httplib.HTTPConnection('localhost', 8080))
        return

    def tearDown(self):
        """clean up after each test"""
        for i in xrange(self.n_connections):
            self.connections[i].close()
        return

    def request(self, *args):
        hc = self.connections[self.next_connection]
        self.next_connection += 1
        hc.request(*args)
        return hc.getresponse()

class TestGetRoot(BaseDataTest):

    n_connections = 1

    def test(self):

        """test GET / (should return 405 Method Not Allowed)"""

        r = self.request('GET', '/')
        headers = dict(r.getheaders())
        assert r.status == 405
        assert r.reason == 'Method Not Allowed'
        assert 'content-length' in headers
        assert headers['content-length'] == '0'
        assert r.read() == ''
        return

class Test404(BaseDataTest):

    """test GET /somethingbogus (should return 404 Not Found)"""

    n_connections = 1

    def test(self):

        r = self.request('GET', '/thisshouldnotexist')
        headers = dict(r.getheaders())
        assert r.status == 404
        assert r.reason == 'Not Found'
        assert 'content-length' in headers
        assert headers['content-length'] == '0'
        assert r.read() == ''
        return

class TestPostGetDelete(BaseDataTest):

    """test POST/GET/DELETE"""

    n_connections = 4

    def test(self):

        data = str(uuid.uuid4())

        r = self.request('POST', '/', data)
        assert r.status == 201
        assert r.reason == 'Created'
        headers = dict(r.getheaders())
        assert 'content-length' in headers
        assert headers['content-length'] == '0'
        assert 'location' in headers
        ident = headers['location'].split('/')[-1]
        assert r.read() == ''

        r = self.request('GET', '/%s' % ident)
        assert r.status == 200
        assert r.reason == 'OK'
        headers = dict(r.getheaders())
        assert 'content-length' in headers
        try:
            content_length = int(headers['content-length'])
        except ValueError:
            self.fail('content-length is not an integer')
        assert content_length == len(data)
        assert r.read() == data

        r = self.request('DELETE', '/%s' % ident)
        assert r.status == 204
        assert r.reason == 'No Content'
        assert r.read() == ''

        r = self.request('GET', '/%s' % ident)
        assert r.status == 410
        assert r.reason == 'Gone'
        headers = dict(r.getheaders())
        assert 'content-length' in headers
        try:
            content_length = int(headers['content-length'])
        except ValueError:
            self.fail('content-length is not an integer')
        assert content_length == 0
        assert r.read() == ''

        return

class TestMediaType(BaseDataTest):

    """test media types"""

    n_connections = 6

    def test(self):

        data = str(uuid.uuid4())

        r = self.request('POST', '/', data, {'Content-Type': 'ctmaj/ctmin'})
        headers = dict(r.getheaders())
        ident = headers['location'].split('/')[-1]

        r = self.request('GET', '/%s' % ident, '', {'Accept': '*/*'})
        assert r.status == 200
        assert r.reason == 'OK'
        headers = dict(r.getheaders())
        assert headers.has_key('content-type')
        assert headers['content-type'] == 'ctmaj/ctmin'
        assert r.read() == data

        r = self.request('GET', '/%s' % ident, '', {'Accept': 'ctmaj/*'})
        assert r.status == 200
        assert r.reason == 'OK'
        headers = dict(r.getheaders())
        assert headers.has_key('content-type')
        assert headers['content-type'] == 'ctmaj/ctmin'
        assert r.read() == data

        r = self.request('GET', '/%s' % ident, '', {'Accept': 'ctmaj/ctmin'})
        assert r.status == 200
        assert r.reason == 'OK'
        headers = dict(r.getheaders())
        assert headers.has_key('content-type')
        assert headers['content-type'] == 'ctmaj/ctmin'
        assert r.read() == data

        r = self.request('GET', '/%s' % ident, '', {'Accept': 'text/*'})
        assert r.status == 406
        assert r.reason == 'Not Acceptable'
        assert r.read() == ''

        r = self.request('GET', '/%s' % ident, '', {'Accept': 'text/plain'})
        assert r.status == 406
        assert r.reason == 'Not Acceptable'
        assert r.read() == ''

class TestValidator(BaseDataTest):

    """test a media type validator"""

    n_connections = 1

    def test(self):

        r = self.request('POST', '/', ',', {'Content-Type': 'application/json'})
        assert r.status == 400
        assert r.reason == 'Bad Request'

class TestConverter(BaseDataTest):

    """test a media type converter"""

    n_connections = 2

    def test(self):

        data = '1,2\na,b\n'
        json_data = '[["1", "2"], ["a", "b"]]'

        r = self.request('POST', '/', data, {'Content-Type': 'text/csv'})
        headers = dict(r.getheaders())
        ident = headers['location'].split('/')[-1]

        r = self.request('GET', 
                         '/%s' % ident, 
                         '', 
                         {'Accept': 'application/json'})
        assert r.status == 200
        assert r.reason == 'OK'
        headers = dict(r.getheaders())
        assert headers.has_key('content-type')
        assert headers['content-type'] == 'application/json'
        assert r.read() == json_data

# eof
