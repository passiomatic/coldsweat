# -*- coding: utf-8 -*-
"""
Description: Cascades through several applications, 
  so long as applications return '404 Not Found'

Copyright (c) 2013—2016 Andrea Peltrin
Portions are copyright (c) 2005 Ian Bicking and contributors
License: MIT (see LICENSE for details)
"""
#import tempfile
from cStringIO import StringIO

from webob.exc import HTTPException, HTTPNotFound
#from coldsweat import log

CHUNK_SIZE = 4096
    
class Cascade(object):

    '''
    Passed a list of applications, ``Cascade`` will try each of them
    in turn.  If one returns a status code listed in ``catch`` (by
    default just ``404 Not Found``) then the next application is
    tried.

    If all applications fail, then the last application's failure
    response is used.

    Instances of this class are WSGI applications.
    '''

    def __init__(self, applications, catch=(HTTPNotFound,)):
        self.apps = applications
        self.catch_codes = {}
        self.catch_exceptions = []
        for error in catch:
            if issubclass(error, HTTPException):
                exc = error
                code = error.code
            else:
                raise ValueError('%s must be a subclass of webob.exc.HTTPException' % error)
            self.catch_codes[code] = exc
            self.catch_exceptions.append(exc)
        self.catch_exceptions = tuple(self.catch_exceptions)
                
    def __call__(self, environ, start_response):
        '''
        WSGI application interface
        '''

        try:
            length = int(environ.get('CONTENT_LENGTH', 0) or 0)
        except ValueError:
            length = 0

        # POST/PUT request: copy wsgi.input
        if length > 0:
            copy_wsgi_input = True
            f = environ['wsgi.input']
            if length < 0:
                data = f.read()
            else:
                data = f.read(length)
            environ['wsgi.input'] = StringIO(data)
        else:
            copy_wsgi_input = False

        def repl_start_response(status, headers, exc_info=None):
            code = status.split(None, 1)[0]
            if int(code) in self.catch_codes:
                failed.append(None)
                return _consuming_writer
            return start_response(status, headers, exc_info)

        apps = list(self.apps)
        last_app = apps.pop()

        for app in apps:

            environ_copy = environ.copy()
            if copy_wsgi_input:
                environ_copy['wsgi.input'].seek(0)
            failed = []
            try:
                app_iter = app(environ_copy, repl_start_response)
                if not failed:
                    return app_iter
                else:
                    if hasattr(app_iter, 'close'):
                        # Exhaust the iterator first, then close
                        tuple(app_iter)
                        app_iter.close()
            except self.catch_exceptions, exc:
                pass

        # Try last app
        if copy_wsgi_input:
            environ['wsgi.input'].seek(0)
        return last_app(environ, start_response)

def _consuming_writer(s):
    pass
