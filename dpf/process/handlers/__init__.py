# See file COPYING distributed with dpf for copyright and license.

import os
import subprocess
import tempfile
import re
import json
import dpf

sge_submit_re = re.compile('Your job (\d+) \(.*\) has been submitted')
media_type_re = re.compile('^[A-Za-z0-9\-\+\.]+/[A-Za-z0-9\-\+\.]+$')

class BaseProcessHandler:

    """base class for process handlers"""

    def __init__(self):
        return

    def _get_data(self, job_dir):
        """return the data sent with the launch (POST) request"""
        return open(os.path.join(job_dir, 'data')).read()

    def _get_content_type(self, job_dir):
        """return the content-type sent with the launch (POST) request, 
        or None if none was given
        """
        ct_fname = os.path.join(job_dir, 'content-type')
        if not os.path.exists(ct_fname):
            return None
        return open(ct_fname).read()

class BaseSGEHandler(BaseProcessHandler):

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

class ScriptHandler(BaseProcessHandler):

    def _execute(self, args):
        with tempfile.TemporaryFile() as fo_out:
            with open(os.devnull, 'w') as fo_err:
                command = [self.script]
                command.extend(args)
                returncode = subprocess.call(command, 
                                             stdout=fo_stdout, 
                                             stderr=fo_stderr)
            fo_out.seek(0)
            stdout = fo_out.read()
        return (returncode, stdout)

    def _split_output(self, data):
        """_split_output(data) -> (media_type, content)

        split script output into a media type and message content

        the media type is checked and ValueError is raised if it is malformed
        if the media type 
        """
        if '\n' not in data:
            raise ValueError('not enough lines in output')
        (media_type, content) = data.split('\n', 1)
        if not re.search(media_type):
            raise ValueError('bad media type: %s' % media_type)
        return (media_type, content)

    def __init__(self, script):
        BaseProcessHandler.__init__(self)
        self.script = script
        (returncode, stdout) = self._execute('description')
        if returncode != 0:
            raise ValueError('"%s description" returned %d' % (self.script, 
                                                               returncode))
        self.description = stdout.strip()
        return

    def get_doc(self, accept):
        (returncode, stdout) = self._execute(['doc', accept])
        if returncode == 40:
            raise dpf.HTTP400BadRequest()
        if returncode == 6:
            raise dpf.HTTP406NotAcceptable()
        if returncode != 0:
            raise ValueError('"%s doc" returned %d' % (self.script, returncode))
        return self._split_output(stdout)

    def launch(self, job_dir):
        (returncode, stdout) = self._execute(['launch', job_dir])
        if returncode == 40:
            raise dpf.HTTP400BadRequest()
        if returncode == 15:
            raise dpf.HTTP415UnsupportedMediaType()
        if returncode != 0:
            raise ValueError('"%s doc" returned %d' % (self.script, returncode))
        return

    def info(self, accept, job_dir):
        (returncode, stdout) = self._execute(['info', accept, job_dir])
        if returncode == 40:
            raise dpf.HTTP400BadRequest()
        if returncode == 6:
            raise dpf.HTTP406NotAcceptable()
        if returncode != 0:
            raise ValueError('"%s doc" returned %d' % (self.script, returncode))
        return self._split_output(stdout)

    def get_subpart(self, accept, job_dir, subpart):
        args = ['subpart', accept, job_dir, subpart]
        (returncode, stdout) = self._execute(args)
        if returncode == 40:
            raise dpf.HTTP400BadRequest()
        if returncode == 4:
            raise dpf.HTTP404NotFound()
        if returncode == 6:
            raise dpf.HTTP406NotAcceptable()
        if returncode != 0:
            raise ValueError('"%s doc" returned %d' % (self.script, returncode))
        return self._split_output(stdout)

    def delete(self, job_dir):
        (returncode, stdout) = self._execute(['delete', job_dir])
        if returncode != 0:
            raise ValueError('"%s doc" returned %d' % (self.script, returncode))
        return

# eof
