# See file COPYING distributed with dpf for copyright and license.

import dpf
from . import BaseProcessHandler, BaseSGEHandler
import json

class WCHandler(BaseSGEHandler):

    """handler for wc"""

    def __init__(self):
        BaseSGEHandler.__init__(self)
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

        self._launch_sge(job_dir, ['wc.sge', data])
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
