# See file COPYING distributed with dpf for copyright and license.

import os
import subprocess
import socket
import time
import uuid
import httplib
import json

class test_data:

    @classmethod
    def setUpClass(cls):

        """set up the data test class

        this will create tmp/data if needed and start the data server
        """

        if not os.path.exists('tmp'):
            os.mkdir('tmp')
        if not os.path.exists('tmp/data'):
            os.mkdir('tmp/data')
        cls.fo_out = open('tmp/data_test.stdout', 'a')
        cls.fo_err = open('tmp/data_test.stderr', 'a')
        cls.po = subprocess.Popen(['dpf_data_server', 
                                   '-C', 'tmp/data', 
                                   '-H', 'dpf.data.handlers.CSVHandler', 
                                   '-H', 'dpf.data.handlers.JSONHandler'],
                                  stdout=cls.fo_out, 
                                  stderr=cls.fo_err)

        # wait for the data server to be listening
        # if it doesn't come up after a certain amount of time, clean up and 
        # then assert False to indicate an error

        for i in xrange(5):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.connect(('localhost', 8080))
            except socket.error:
                time.sleep(1)
                pass
            else:
                break
            finally:
                s.close()
        else:
            cls.po.terminate()
            cls.fo_out.close()
            cls.fo_err.close()
            assert False
        return

    @classmethod
    def tearDownClass(cls):

        """clean up after the data tests

        this just stops the data server and closes its output file objects

        the server cache directory is left in place
        """
        
        cls.po.terminate()
        cls.fo_out.close()
        cls.fo_err.close()
        return


    def setUp(self):

        """set up each test

        prepare the connections to the data server
        """

        self.hc = httplib.HTTPConnection('localhost', '8080')
        self.hc2 = httplib.HTTPConnection('localhost', '8080')
        self.hc3 = httplib.HTTPConnection('localhost', '8080')
        self.hc4 = httplib.HTTPConnection('localhost', '8080')
        self.hc5 = httplib.HTTPConnection('localhost', '8080')
        self.hc6 = httplib.HTTPConnection('localhost', '8080')
        return

    def tearDown(self):

        """clean up after each test"""

        self.hc.close()
        self.hc2.close()
        self.hc3.close()
        self.hc4.close()
        self.hc5.close()
        self.hc6.close()
        return

    def test_get_root(self):

        """test GET / (should return 405 Method Not Allowed)"""

        self.hc.request('GET', '/')
        r = self.hc.getresponse()
        headers = dict(r.getheaders())
        assert r.status == 405
        assert r.reason == 'Method Not Allowed'
        assert 'content-length' in headers
        assert headers['content-length'] == '0'
        assert r.read() == ''
        return

    def test_404(self):

        """test GET /somethingbogus (should return 404 Not Found)"""

        self.hc.request('GET', '/thisshouldnotexist')
        r = self.hc.getresponse()
        headers = dict(r.getheaders())
        assert r.status == 404
        assert r.reason == 'Not Found'
        assert 'content-length' in headers
        assert headers['content-length'] == '0'
        assert r.read() == ''
        return

    def test_post_get_delete(self):

        """test POST/GET/DELETE"""

        data = str(uuid.uuid4())

        self.hc.request('POST', '/', data)
        r = self.hc.getresponse()
        assert r.status == 201
        assert r.reason == 'Created'
        headers = dict(r.getheaders())
        assert 'content-length' in headers
        assert headers['content-length'] == '0'
        assert 'location' in headers
        ident = headers['location'].split('/')[-1]
        assert r.read() == ''

        self.hc2.request('GET', '/%s' % ident)
        r = self.hc2.getresponse()
        assert r.status == 200
        assert r.reason == 'OK'
        headers = dict(r.getheaders())
        assert 'content-length' in headers
        try:
            content_length = int(headers['content-length'])
        except ValueError:
            self.fail('content-length is not an integer')
        assert r.read() == data

        self.hc2.request('DELETE', '/%s' % ident)
        r = self.hc2.getresponse()
        assert r.status == 204
        assert r.reason == 'No Content'
        assert r.read() == ''

        self.hc2.request('GET', '/%s' % ident)
        r = self.hc2.getresponse()
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

    def test_media_type(self):

        """test media types"""

        data = str(uuid.uuid4())

        self.hc.request('POST', '/', data, {'Content-Type': 'ctmaj/ctmin'})
        r = self.hc.getresponse()
        headers = dict(r.getheaders())
        ident = headers['location'].split('/')[-1]

        self.hc2.request('GET', '/%s' % ident, '', {'Accept': '*/*'})
        r = self.hc2.getresponse()
        assert r.status == 200
        assert r.reason == 'OK'
        headers = dict(r.getheaders())
        assert headers.has_key('content-type')
        assert headers['content-type'] == 'ctmaj/ctmin'
        assert r.read() == data

        self.hc3.request('GET', '/%s' % ident, '', {'Accept': 'ctmaj/*'})
        r = self.hc3.getresponse()
        assert r.status == 200
        assert r.reason == 'OK'
        headers = dict(r.getheaders())
        assert headers.has_key('content-type')
        assert headers['content-type'] == 'ctmaj/ctmin'
        assert r.read() == data

        self.hc4.request('GET', '/%s' % ident, '', {'Accept': 'ctmaj/ctmin'})
        r = self.hc4.getresponse()
        assert r.status == 200
        assert r.reason == 'OK'
        headers = dict(r.getheaders())
        assert headers.has_key('content-type')
        assert headers['content-type'] == 'ctmaj/ctmin'
        assert r.read() == data

        self.hc5.request('GET', '/%s' % ident, '', {'Accept': 'text/*'})
        r = self.hc5.getresponse()
        assert r.status == 406
        assert r.reason == 'Not Acceptable'
        assert r.read() == ''

        self.hc6.request('GET', '/%s' % ident, '', {'Accept': 'text/plain'})
        r = self.hc6.getresponse()
        assert r.status == 406
        assert r.reason == 'Not Acceptable'
        assert r.read() == ''

    def test_validator(self):

        """test a media type validator"""

        self.hc.request('POST', '/', ',', {'Content-Type': 'text/json'})
        r = self.hc.getresponse()
        assert r.status == 400
        assert r.reason == 'Bad Request'

    def test_converter(self):

        """test a media type converter"""

        data = '1,2\na,b\n'
        json_data = '[["1", "2"], ["a", "b"]]'

        self.hc.request('POST', '/', data, {'Content-Type': 'text/csv'})
        r = self.hc.getresponse()
        headers = dict(r.getheaders())
        ident = headers['location'].split('/')[-1]

        self.hc2.request('GET', '/%s' % ident, '', {'Accept': 'text/json'})
        r = self.hc2.getresponse()
        assert r.status == 200
        assert r.reason == 'OK'
        headers = dict(r.getheaders())
        assert headers.has_key('content-type')
        assert headers['content-type'] == 'text/json'
        assert r.read() == json_data

# eof
