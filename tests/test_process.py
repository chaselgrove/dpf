# See file COPYING distributed with dpf for copyright and license.

import os
import subprocess
import socket
import time
import httplib
from . import start_process_server, start_data_server, stop_server

test_vars = {}

def setup():
    (po, fo_out, fo_err) = start_data_server()
    test_vars['data_po'] = po
    test_vars['data_fo_out'] = fo_out
    test_vars['data_fo_err'] = fo_err
    (po, fo_out, fo_err) = start_process_server()
    test_vars['process_po'] = po
    test_vars['process_fo_out'] = fo_out
    test_vars['process_fo_err'] = fo_err
    return

def teardown():
    stop_server(test_vars['data_po'], 
                test_vars['data_fo_out'], 
                test_vars['data_fo_err'])
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

class TestRoot(BaseProcessTest):

    n_process_connections = 1

    def test(self):
        r = self.process_request('GET', '/')
        r.status = 200
        r.reason = 'OK'
        assert '    /wc' in r.read()
        return

# eof
