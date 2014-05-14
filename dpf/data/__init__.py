# See file COPYING distributed with dpf for copyright and license.

import os
import traceback
import shutil
import random
import time
import json
import wsgiref.util
import dpf

read_size = 1024*1024

class Application(dpf.Application):

    def __init__(self, base_dir, data_handlers):
        self.base_dir = base_dir
        self.data_handlers = {}
        for dh_class in data_handlers:
            self.data_handlers[dh_class.from_type] = dh_class
        return

    def __call__(self, environ, start_response):
        try:
            path = environ['PATH_INFO']
            if not path:
                path = '/'
            if path == '/':
                (status, headers, oi) = self.handle_root(environ)
            else:
                ident = path.strip('/')
                (status, headers, oi) = self.handle_data(environ, ident)
            start_response(status, headers)
            return oi
        except dpf.BaseHTTPError, exc:
            status = exc.status
            if exc.content_type:
                output = exc.content
                headers = [('Content-type', exc.content_type),
                        ('Content-Length', str(len(output)))]
            else:
                output = ''
                headers = [('Content-Length', '0')]
        except:
            traceback.print_exc()
            status = '500 Internal Server Error'
            output = 'A server error occurred.  ' + \
                     'Please contact the administrator.\n'
            headers = [('Content-Type', 'text/plain'),
                       ('Content-Length', str(len(output)))]
        start_response(status, headers)
        return [output]

    def handle_root(self, environ):

        if environ['REQUEST_METHOD'] == 'POST':

            try:
                content_length = int(environ['CONTENT_LENGTH'])
            except KeyError:
                raise dpf.HTTP411LengthRequired()
            except ValueError:
                raise dpf.HTTP400BadRequest('text/plain', 'Bad content-length.\n')

            if content_length < 0:
                raise dpf.HTTP400BadRequest('text/plain', 'Bad content-length.\n')

            # check that content-type is in two parts separated by a slash
            if 'CONTENT_TYPE' not in environ:
                raise dpf.HTTP400BadRequest('text/plain', 'No content-type.\n')
            if len(environ['CONTENT_TYPE'].split('/')) != 2:
                raise dpf.HTTP400BadRequest('text/plain', 'Bad content-type.\n')

            while True:
                ident = '%08x' % random.getrandbits(32)
                dir = os.path.join(self.base_dir, ident)
                if not os.path.exists(dir):
                    break
            os.mkdir(dir)

            fname = 'data'
            full_fname = os.path.join(dir, fname)
            fo = open(full_fname, 'w')
            bytes_remaining = content_length
            while bytes_remaining:
                if bytes_remaining > read_size:
                    n_to_read = read_size
                else:
                    n_to_read = bytes_remaining
                data = environ['wsgi.input'].read(n_to_read)
                fo.write(data)
                bytes_remaining -= n_to_read
            fo.close()

            if environ['CONTENT_TYPE'] in self.data_handlers:
                dh_class = self.data_handlers[environ['CONTENT_TYPE']]
                data_handler = dh_class()
                if not data_handler.validate(full_fname):
                    shutil.rmtree(dir)
                    msg = 'Data did not validate against content-type.\n'
                    raise dpf.HTTP400BadRequest('text/plain', msg)

            d = {'source content type': environ['CONTENT_TYPE'], 
                'creation time': int(time.time()), 
                'data': {environ['CONTENT_TYPE']: fname}}

            fo = open(os.path.join(dir, 'info.json'), 'w')
            json.dump(d, fo)
            fo.close()

            app_uri = wsgiref.util.application_uri(environ).rstrip('/')
            headers = [('Location', '%s/%s' % (app_uri, ident)), 
                    ('Content-Length', '0')]
            oi = ['']
            return ('201 Created', headers, oi)

        raise dpf.HTTP405MethodNotAllowed(['GET', 'POST'])

    def handle_data(self, environ, ident):

        if ident not in os.listdir(self.base_dir):
            raise dpf.HTTP404NotFound()

        if not os.path.exists(os.path.join(self.base_dir, ident, 'info.json')):
            raise dpf.HTTP410Gone()

        if environ['REQUEST_METHOD'] == 'DELETE':
            for fname in os.listdir(os.path.join(self.base_dir, ident)):
                os.unlink(os.path.join(self.base_dir, ident, fname))
            headers = []
            oi = ['']
            return ('204 No Content', headers, oi)

        if environ['REQUEST_METHOD'] in ('HEAD', 'GET'):

            d = json.load(open(os.path.join(self.base_dir, ident, 'info.json')))

            source_content_type = d['source content type']

            available_types = [source_content_type]

            if source_content_type in self.data_handlers:
                to_types = self.data_handlers[source_content_type].to_types
                available_types.extend(to_types)

            content_type = dpf.choose_media_type(environ, available_types)

            fname = os.path.join(self.base_dir, ident, 'data')

            if content_type == source_content_type:
                data = open(fname).read()
            else:
                dh_class = self.data_handlers[source_content_type]
                data_handler = dh_class()
                data = data_handler.convert(fname, content_type)

            tt = time.gmtime(d['creation time'])
            time_string = time.strftime('%a, %d %b %Y %H:%M:%S GMT', tt)

            headers = [('Content-Type', str(content_type)), 
                        ('Content-Length', str(len(data))), 
                        ('Last-Modified', time_string)]

            if environ['REQUEST_METHOD'] == 'HEAD':
                return ('200 OK', headers, [''])

            return ('200 OK', headers, [data])

        raise dpf.HTTP405MethodNotAllowed(['HEAD', 'GET', 'DELETE'])

# eof
