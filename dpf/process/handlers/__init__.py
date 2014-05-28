# See file COPYING distributed with dpf for copyright and license.

import os
import subprocess
import re
import json
import dpf

sge_submit_re = re.compile('Your job (\d+) \(.*\) has been submitted')

class BaseProcessHandler:

    """base class for process handlers"""

    def __init__(self):
        return

    def _get_data(self, job_dir):
        """return the data sent with the launch (POST) request"""
        return open(os.path.join(job_dir, 'data')).read()

    def _get_content_type(self, job_dir):
        """return the content-type sent with the launch (POST) request, or None if none was given"""
        ct_fname = os.path.join(job_dir, 'content-type')
        if not os.path.exists(ct_fname):
            return None
        return open(ct_fname).read()

class SGEHandler(BaseProcessHandler):

    """base class for handlers using SGE"""

    def _get_job_id(self, job_dir):
        fname = os.path.join(job_dir, 'job_id')
        return int(open(fname).read())

    def _get_job_status(self, job_dir):

        job_id = self._get_job_id(job_dir)

        po = subprocess.Popen(['qstat'], stdout=subprocess.PIPE)
        stdout = po.communicate()[0]
        assert po.returncode == 0

        # default if the job is not found in qstat
        status = 'completed'

        for line in stdout.split('\n'):
            if line.startswith('job-ID') or line.startswith('------'):
                continue
            fields = line.split()
            if not fields:
                continue
            line_id = int(fields[0])
            if line_id == job_id:
                if fields[4] == 'r':
                    status = 'running'
                elif fields[4] == 'qw':
                    status = 'queued'
                elif 'E' in fields[4]:
                    status = 'error'
                else:
                    msg = 'unhandled value "%s" for job status' % fields[4]
                    raise ValueError(msg)

        return status

    def info(self, accept, job_dir):
        d = {'job_id': self._get_job_id(job_dir), 
             'job_status': self._get_job_status(job_dir)}
        if d['job_status'] not in ('queued', 'error'):
            d['stdout'] = 'stdout'
            d['stderr'] = 'stderr'
        mt = dpf.choose_media_type(accept, ['text/plain', 'application/json'])
        if mt == 'text/plain':
            output = ''
            for key in ('job_id', 'job_status', 'stdout', 'stderr'):
                if key in d:
                    output += '%s: %s\n' % (key, d[key])
        else:
            output = json.dumps(d)
        return (mt, output)

    def get_subpart(self, accept, job_dir, subpart):

        status = self._get_job_status(job_dir)

        if subpart == 'stdout':
            if status in ('queued', 'error'):
                raise dpf.HTTP404NotFound()
            dpf.choose_media_type(accept, ['text/plain'])
            fname = os.path.join(job_dir, 'stdout')
            if not os.path.exists(fname):
                output = ''
            else:
                output = open(fname).read()
            headers = [('Content-Type', 'text/plain'),
                       ('Content-Length', str(len(output)))]
            return ('200 OK', headers, [output])

        if subpart == 'stderr':
            if status in ('queued', 'error'):
                raise dpf.HTTP404NotFound()
            fname = os.path.join(job_dir, 'stderr')
            if not os.path.exists(fname):
                output = ''
            else:
                output = open(fname).read()
            dpf.choose_media_type(accept, ['text/plain'])
            headers = [('Content-Type', 'text/plain'),
                       ('Content-Length', str(len(output)))]
            return ('200 OK', headers, [output])

        raise dpf.HTTP404NotFound()

    def _launch_sge(self, job_dir, extra_args):

        args = ['qsub',
                '-S',
                '/bin/bash',
                '-o',
                os.path.join(job_dir, 'stdout'),
                '-e',
                os.path.join(job_dir, 'stderr')]

        args.extend(extra_args)

        po = subprocess.Popen(args, stdout=subprocess.PIPE)
        po.wait()

        # errors here rise to the base handler and return 500,which is 
        # as desired
        assert po.returncode == 0
        mo = sge_submit_re.match(po.stdout.read())
        self.job_id = int(mo.groups()[0])

        fo = open(os.path.join(job_dir, 'job_id'), 'w')
        fo.write('%d\n' % self.job_id)
        fo.close()

        return

    def delete(self, job_dir):
        args = ['qdel', str(self._get_job_id(job_dir))]
        po = subprocess.Popen(args, stdout=subprocess.PIPE)
        po.wait()
        return

class WCHandler(SGEHandler):

    """handler for wc"""

    def __init__(self):
        SGEHandler.__init__(self)
        self.description = 'word count (wc)'
        return

    def get_doc(self, accept):
        mt = dpf.choose_media_type(accept, ['text/plain', 'application/json'])
        if mt == 'text/plain':
            output = 'wc\n'
        else:
            output = json.dumps('wc json') + '\n'
        return (mt, output)

    def launch(self, job_dir):

        data = self._get_data(job_dir)
        content_type = self._get_content_type(job_dir)
        if content_type is None:
            content_type = 'text/plain'

        if content_type != 'text/plain':
            raise dpf.HTTP415UnsupportedMediaType()
        if not data.startswith('http://'):
            raise dpf.HTTP400BadRequest('text/plain',
                                        'data must contain a URL\n')

        self._launch_sge(job_dir, ['/Users/ch/Desktop/umms/dpf/wc.sge', data])
        return

class EchoHandler(BaseProcessHandler):

    """this handler does nothing

    no validation is done of the input

    stdout contains the input and stderr is empty

    no job is actually launched
    """

    def __init__(self):
        BaseProcessHandler.__init__(self)
        self.description = 'echo the input to stdout'
        return

    def get_doc(self, accept):
        mt = dpf.choose_media_type(accept, ['text/plain', 'application/json'])
        if mt == 'text/plain':
            output = 'echo the input to stdout\n'
        else:
            output = json.dumps('echo the input to stdout') + '\n'
        return (mt, output)

    def launch(self, job_dir):
        return

    def info(self, accept, job_dir):
        data = self._get_data(job_dir)
        content_type = self._get_content_type(job_dir)
        d = {'process': 'echo', 
             'content type': content_type, 
             'data length': len(data)}
        mt = dpf.choose_media_type(accept, ['text/plain', 'application/json'])
        if mt == 'text/plain':
            output = ''
            for key in ('process', 'content type', 'data length'):
                if key in d:
                    output += '%s: %s\n' % (key, d[key])
        else:
            output = json.dumps(d)
        return (mt, output)

    def get_subpart(self, accept, job_dir, subpart):
        content_type = self._get_content_type(job_dir)
        if subpart == 'stdout':
            mt = dpf.choose_media_type(accept, [content_type])
            output = self._get_data(job_dir)
            return(mt, output)
        if subpart == 'stderr':
            mt = dpf.choose_media_type(accept, ['text/plain'])
            return (mt, '')
        raise dpf.HTTP404NotFound()

    def delete(self, job_dir):
        return

# eof
