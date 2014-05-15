# See file COPYING distributed with dpf for copyright and license.

import os
import traceback
import tempfile
import shutil
import wsgiref
import sqlite3
import json
import dpf

db_ddl = """CREATE TABLE job (id TEXT NOT NULL PRIMARY KEY,
                              process TEXT NOT NULL,
                              deleted BOOLEAN NOT NULL DEFAULT 0);"""

def sqlite_convert_boolean(i):
    if i == '1':
        return True
    return False

def sqlite_adapt_boolean(b):
    if b:
        return 1
    return 0

sqlite3.register_adapter(bool, sqlite_adapt_boolean)
sqlite3.register_converter('boolean', sqlite_convert_boolean)

class Application(dpf.Application):

    def __init__(self, base_dir, process_handlers):
        self.base_dir = base_dir
        self.process_handlers = {}
        for (label, ph) in process_handlers.iteritems():
            label = label.strip('/')
            # The process handler class may be configured with extra arguments 
            # to __init__().  If none are given (just the class is passed), 
            # we explicitly store no extra arguments.
            if not isinstance(ph, (tuple, list)):
                self.process_handlers[label] = (ph, ())
            else:
                self.process_handlers[label] = ph
        self.db_fname = os.path.join(self.base_dir, 'jobs.sqlite')
        if not os.path.exists(self.db_fname):
            db = sqlite3.connect(self.db_fname)
            c = db.cursor()
            c.execute(db_ddl)
            c.close()
            db.commit()
            db.close()
        return

    def __call__(self, environ, start_response):
        try:
            path = environ['PATH_INFO']
            if not path:
                path = '/'
            if path == '/':
                (status, headers, oi) = self.handle_root(environ)
            elif path.startswith('/job/'):
                (status, headers, oi) = self.handle_job(environ)
            else:
                (status, headers, oi) = self.handle_process(environ)
            start_response(status, headers)
            return oi
        except dpf.BaseHTTPError, exc:
            status = exc.status
            headers = exc.headers
            output = exc.content
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

        if environ['REQUEST_METHOD'] == 'GET':
            mt = dpf.choose_media_type(environ, ['text/plain', 'text/json'])
            if mt == 'text/plain':
                output = 'Available:\n'
                for label in sorted(self.process_handlers):
                    (ph_class, ph_args) = self.process_handlers[label]
                    ph = ph_class(environ, *ph_args)
                    description = ph.get_description()
                    output += '    /%s: %s\n' % (label, description)
            else:
                l = {}
                for label in sorted(self.process_handlers):
                    (ph_class, ph_args) = self.process_handlers[label]
                    ph = ph_class(environ, *ph_args)
                    description = ph.get_description()
                    l['/%s' % label] = description
                output = json.dumps(l) + '\n'
            headers = [('Content-Type', mt),
                       ('Content-Length', str(len(output)))]
            oi = [output]
            return ('200 OK', headers, oi)

        raise dpf.HTTP405MethodNotAllowed(['GET'])

    def handle_process(self, environ):

        path = environ['PATH_INFO']

        try:
            process_name = path.strip('/')
            (ph_class, ph_args) = self.process_handlers[process_name]
        except KeyError:
            raise dpf.HTTP404NotFound()

        ph = ph_class(environ, *ph_args)

        if environ['REQUEST_METHOD'] == 'GET':
            (content_type, output) = ph.get_doc()
            headers = [('Content-Type', content_type),
                       ('Content-Length', str(len(output)))]
            oi = [output]
            return ('200 OK', headers, oi)

        if environ['REQUEST_METHOD'] == 'POST':

            try:
                content_length = int(environ['CONTENT_LENGTH'])
            except KeyError:
                raise dpf.HTTP411LengthRequired()
            except ValueError:
                raise dpf.HTTP400BadRequest('text/plain', 
                                            'Bad content-length.\n')

            if content_length < 0:
                raise dpf.HTTP400BadRequest('text/plain', 
                                            'Bad content-length.\n')

            if 'CONTENT_TYPE' not in environ:
                raise dpf.HTTP400BadRequest('text/plain', 'No content-type.\n')

            data = environ['wsgi.input'].read(content_length)

            job_dir = tempfile.mkdtemp(prefix='', dir=self.base_dir)
            try:
                ident = os.path.basename(job_dir)
                open(os.path.join(job_dir, 'data'), 'w').write(data)
                ph.set_working_dir(job_dir)
                ph.accept()
            except:
                shutil.rmtree(job_dir)
                raise

            self.register_job(ident, process_name)

            ph.launch()

            app_uri = wsgiref.util.application_uri(environ).rstrip('/')
            headers = [('Location', '%s/job/%s' % (app_uri, ident)), 
                       ('Content-Length', '0')]
            return ('201 Created', headers, [''])

        raise dpf.HTTP405MethodNotAllowed(['GET', 'POST'])

    def handle_job(self, environ):

        assert environ['PATH_INFO'].startswith('/job/')
        ident = environ['PATH_INFO'][5:].split('/')[0]

        try:
            job_dict = self.get_job(ident)
        except ValueError:
            raise dpf.HTTP404NotFound()

        if job_dict['deleted']:
            raise dpf.HTTP410Gone()

        (ph_class, ph_args) = self.process_handlers[job_dict['process']]
        ph = ph_class(environ, *ph_args)
        ph.set_working_dir(os.path.join(self.base_dir, ident))
        job_url = '/job/%s' % ident

        if environ['REQUEST_METHOD'] == 'GET':

            if environ['PATH_INFO'] == job_url or \
            environ['PATH_INFO'] == job_url+'/':
                (content_type, output) = ph.info()
                headers = [('Content-Type', content_type),
                           ('Content-Length', str(len(output)))]
                oi = [output]
                return ('200 OK', headers, oi)

            subpath = environ['PATH_INFO'][len(job_url)+1:]
            return ph.get_subpart(subpath)

        if environ['REQUEST_METHOD'] == 'DELETE':

            if environ['PATH_INFO'] == job_url or \
               environ['PATH_INFO'] == job_url+'/':
                self.delete_job(ident)
                ph.delete()
                shutil.rmtree(ph.working_dir)
                return ('204 No Content', [], [''])

            subpath = environ['PATH_INFO'][len(job_url)+1:]

            # we just use this to raise the 404 if the subpart doesn't exist; 
            # if it does...
            ph.get_subpart(subpath)

            # ...fall through to method not allowed
            raise dpf.HTTP405MethodNotAllowed(['GET'])

        raise dpf.HTTP405MethodNotAllowed(['GET', 'DELETE'])

    def register_job(self, ident, process):
        db = sqlite3.connect(self.db_fname, 
                             detect_types=sqlite3.PARSE_DECLTYPES)
        try:
            c = db.cursor()
            c.execute("INSERT INTO job (id, process) VALUES (?, ?)", 
                      (ident, process))
            c.close()
            db.commit()
        finally:
            db.close()
        return

    def get_job(self, ident):
        db = sqlite3.connect(self.db_fname, 
                             detect_types=sqlite3.PARSE_DECLTYPES)
        try:
            c = db.cursor()
            c.execute("SELECT * FROM job WHERE id = ?", (ident, ))
            cols = [ el[0] for el in c.description ]
            row = c.fetchone()
            if not row:
                raise ValueError('no job %s in database' % ident)
            d = dict(zip(cols, row))
            c.close()
        finally:
            db.close()
        return d

    def delete_job(self, ident):
        db = sqlite3.connect(self.db_fname, 
                             detect_types=sqlite3.PARSE_DECLTYPES)
        try:
            c = db.cursor()
            c.execute("UPDATE job SET deleted = ? WHERE id = ?", (True, ident))
            if not c.rowcount:
                raise ValueError('no job %s in database' % ident)
            c.close()
            db.commit()
        finally:
            db.close()
        return

# eof
