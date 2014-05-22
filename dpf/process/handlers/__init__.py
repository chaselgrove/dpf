# See file COPYING distributed with dpf for copyright and license.

import os
import subprocess
import re
import json
import dpf

sge_submit_re = re.compile('Your job (\d+) \(.*\) has been submitted')

class ProcessHandler:

    """base class for process handlers"""

    def __init__(self):
        return

class SGEHandler(ProcessHandler):

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

    def info(self, environ, job_dir):
        d = {'job_id': self._get_job_id(job_dir), 
             'job_status': self._get_job_status(job_dir)}
        if d['job_status'] not in ('queued', 'error'):
            d['stdout'] = 'stdout'
            d['stderr'] = 'stderr'
        mt = dpf.choose_media_type(environ, ['text/plain', 'text/json'])
        if mt == 'text/plain':
            output = ''
            for key in ('job_id', 'job_status', 'stdout', 'stderr'):
                if key in d:
                    output += '%s: %s\n' % (key, d[key])
        else:
            output = json.dumps(d)
        return (mt, output)

    def get_subpart(self, environ, job_dir, subpart):

        status = self._get_job_status(job_dir)

        if subpart == 'stdout':
            if status in ('queued', 'error'):
                raise dpf.HTTP404NotFound()
            dpf.choose_media_type(environ, ['text/plain'])
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
            dpf.choose_media_type(environ, ['text/plain'])
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

    def delete(self, environ, job_dir):
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

    def get_doc(self, environ):
        mt = dpf.choose_media_type(environ, ['text/plain', 'text/json'])
        if mt == 'text/plain':
            output = 'wc\n'
        else:
            output = json.dumps('wc json') + '\n'
        return (mt, output)

    def launch(self, environ, job_dir):

        data = open(os.path.join(job_dir, 'data')).read()
        if environ['CONTENT_TYPE'] != 'text/plain':
            raise dpf.HTTP415UnsupportedMediaType()
        if not data.startswith('http://'):
            raise dpf.HTTP400BadRequest('text/plain',
                                        'data must contain a URL\n')

        self._launch_sge(job_dir, ['/Users/ch/Desktop/umms/dpf/wc.sge', data])
        return

# eof
