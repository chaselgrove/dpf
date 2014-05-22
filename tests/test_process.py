# See file COPYING distributed with dpf for copyright and license.

import os
import subprocess
import socket
import time
import httplib
import json
from . import start_process_server, start_data_server, stop_server

test_vars = {}

def setup():
#    (po, fo_out, fo_err) = start_data_server()
#    test_vars['data_po'] = po
#    test_vars['data_fo_out'] = fo_out
#    test_vars['data_fo_err'] = fo_err
    (po, fo_out, fo_err) = start_process_server()
    test_vars['process_po'] = po
    test_vars['process_fo_out'] = fo_out
    test_vars['process_fo_err'] = fo_err
    return

def teardown():
#    stop_server(test_vars['data_po'], 
#                test_vars['data_fo_out'], 
#                test_vars['data_fo_err'])
    stop_server(test_vars['process_po'], 
                test_vars['process_fo_out'], 
                test_vars['process_fo_err'])
    return

class BaseProcessTest:

    """base class for process tests"""

    n_data_connections = 0
    n_process_connections = 0

    def setUp(self):
        """set up each test"""
        self.data_connections = []
        self.process_connections = []
        self.next_data_connection = 0
        self.next_process_connection = 0
        for i in xrange(self.n_data_connections):
            c = httplib.HTTPConnection('localhost', 8080)
            self.data_connections.append(c)
        for i in xrange(self.n_process_connections):
            c = httplib.HTTPConnection('localhost', 8081)
            self.process_connections.append(c)
        return

    def tearDown(self):
        """clean up after each test"""
        for i in xrange(self.n_data_connections):
            self.data_connections[i].close()
        for i in xrange(self.n_process_connections):
            self.process_connections[i].close()
        return

    def data_request(self, *args):
        hc = self.data_connections[self.next_data_connection]
        self.next_data_connection += 1
        hc.request(*args)
        return hc.getresponse()

    def process_request(self, *args):
        hc = self.process_connections[self.next_process_connection]
        self.next_process_connection += 1
        hc.request(*args)
        return hc.getresponse()

class TestGetRoot(BaseProcessTest):

    n_process_connections = 3

    def test(self):
        r = self.process_request('GET', '/')
        r.status = 200
        r.reason = 'OK'
        assert '    wc' in r.read()
        return

    def test_accept(self):
        r = self.process_request('GET', '/', '', {'Accept': 'text/json'})
        r.status = 200
        r.reason = 'OK'
        data = r.read()
        try:
            obj = json.loads(data)
        except:
            self.fail('returned data was not json')
        assert isinstance(obj, dict)
        assert 'wc' in obj
        return

    def test_accept_bad(self):
        r = self.process_request('GET', '/', '', {'Accept': 'ctmaj/ctmin'})
        r.status = 406
        r.reason = 'Not Acceptable'
        assert r.read() == ''
        return

class Test404(BaseProcessTest):

    n_process_connections = 1

    def test(self):
        r = self.process_request('GET', '/thisshouldnotexist')
        r.status = 404
        r.reason = 'Not Found'
        return

class TestPostGetDelete(BaseProcessTest):

    n_process_connections = 4

    def test(self):

        headers = {'Content-Type': 'text/plain'}
        r = self.process_request('POST', '/echo', 'data', headers)
        assert r.status == 201
        assert r.reason == 'Created'
        headers = dict(r.getheaders())
        assert 'content-length' in headers
        assert headers['content-length'] == '0'
        assert 'location' in headers
        ident = headers['location'].split('/')[-1]
        assert r.read() == ''

        r = self.process_request('GET', '/job/%s' % ident)
        assert r.status == 200
        assert r.reason == 'OK'
        headers = dict(r.getheaders())
        assert 'content-length' in headers
        try:
            content_length = int(headers['content-length'])
        except ValueError:
            self.fail('content-length is not an integer')
        assert len(r.read()) == content_length

        r = self.process_request('DELETE', '/job/%s' % ident)
        assert r.status == 204
        assert r.reason == 'No Content'
        assert r.read() == ''

        r = self.process_request('GET', '/job/%s' % ident)
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

class TestValidator(BaseProcessTest):

    """test that a handler's validation presents correctly on the front end"""

    n_process_connections = 3

    def test_okay(self):
        headers = {'Content-Type': 'text/plain'}
        data = 'http://localhost:8081/'
        r = self.process_request('POST', '/wc', data, headers)
        assert r.status == 201
        assert r.reason == 'Created'
        return

    def test_bad_content_type(self):
        headers = {'Content-Type': 'text/json'}
        data = 'http://localhost:8081/'
        r = self.process_request('POST', '/wc', data, headers)
        assert r.status == 415
        assert r.reason == 'Unsupported Media Type'
        return

    def test_bad_request(self):
        headers = {'Content-Type': 'text/plain'}
        r = self.process_request('POST', '/wc', 'bogus', headers)
        assert r.status == 400
        assert r.reason == 'Bad Request'
        return

# eof
