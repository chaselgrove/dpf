# See file COPYING distributed with dpf for copyright and license.

class Application:

    """base class for DPF WSGI applications"""

class BaseHTTPError(Exception):

    """base class for HTTP exceptions"""

    def __init__(self, content_type=None, content=None):
        self.content_type = content_type
        if self.content_type:
            self.content = content
            self.headers = [('Content-type', self.content_type),
                            ('Content-Length', str(len(self.content)))]
        else:
            self.content = ''
            self.headers = [('Content-Length', '0')]
        return

class HTTP400BadRequest(BaseHTTPError):

    status = '400 Bad Request'

class HTTP404NotFound(BaseHTTPError):

    status = '404 Not Found'

class HTTP405MethodNotAllowed(BaseHTTPError):

    status = '405 Method Not Allowed'

    def __init__(self, allowed_methods, content_type=None, content=None):
        BaseHTTPError.__init__(self, content_type, content)
        self.headers.append(('Allow', ', '.join(allowed_methods)))
        return

class HTTP406NotAcceptable(BaseHTTPError):

    status = '406 Not Acceptable'

class HTTP410Gone(BaseHTTPError):

    status = '410 Gone'

class HTTP411LengthRequired(BaseHTTPError):

    status = '411 Length Required'

class HTTP415UnsupportedMediaType(BaseHTTPError):

    status = '415 Unsupported Media Type'

def get_accept(environ):

    """get_accept(environ) -> accept header

    Return the Accept header from the request, or */* if it is not present.

    environ is the WSGI environment variable, from which the Accept header is read.
    """

    if 'HTTP_ACCEPT' in environ:
        return environ['HTTP_ACCEPT']
    return '*/*'

def choose_media_type(accept, resource_types):

    """choose_media_type(accept, resource_types) -> resource type

    select a media type for the response

    accept is the Accept header from the request.  If there is no Accept header, '*/*' is assumed.  If the Accept header cannot be parsed, HTTP400BadRequest is raised.

    resource_types is an ordered list of available resource types, with the most desirable type first.

    To find a match, the types in the Accept header are ordered by q value (descending), and each is compared with the available resource types in order.  The first matching media type is returned.

    If not match is found, HTTP406NotAcceptable is raised.
    """

    # This function is exposed in the script dpf_choose_media_type, 
    # so if changes are made here, that script's documentation 
    # should be updated to reflect them.

    # list of (type, subtype, q)
    accept_types = []

    for part in accept.split(','):
        part = part.strip()
        if ';' not in part:
            mt = part
            q = 1.0
        else:
            (mt, q) = part.split(';', 1)
            mt = mt.strip()
            q = q.strip()
            if not q.startswith('q='):
                raise HTTP400BadRequest('text/plain', 'Bad Accept header.\n')
            try:
                q = float(q[2:])
            except ValueError:
                raise HTTP400BadRequest('text/plain', 'Bad Accept header.\n')
        if '/' not in mt:
            raise HTTP400BadRequest('text/plain', 'Bad Accept header.\n')
        (type, subtype) = mt.split('/', 1)
        accept_types.append((type, subtype, q))

    accept_types.sort(cmp_accept_type)
    accept_types.reverse()

    for (type, subtype, q) in accept_types:
        for available_type in resource_types:
            (a_type, a_subtype) = available_type.split('/', 1)
            if type != '*' and type != a_type:
                continue
            if subtype != '*' and subtype != a_subtype:
                continue
            return available_type

    raise HTTP406NotAcceptable()

def cmp_accept_type(a, b):
    """cmp() for (type, subtype, q) in accept_types in choose_media_type()

    If the q values differ, favor the higher q value, otherwise favor the more specific media type.
    """
    if a[2] != b[2]:
        return cmp(a[2], b[2])
    if a[0] == '*' and b[0] == '*':
        return 0
    if a[0] == '*':
        return -1
    if b[0] == '*':
        return 1
    if a[0] != b[0]:
        return 0
    if a[1] == '*' and b[1] == '*':
        return 0
    if a[1] == '*':
        return -1
    if b[1] == '*':
        return 1
    return 0

# eof
