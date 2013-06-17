# -*- coding: utf-8 -*-
'''
Coldsweat - A Fever clone

Copyright (c) 2013— Andrea Peltrin
Portions are copyright (c) 2013 Rui Carmo
License: MIT (see LICENSE.md for details)
'''
import sys, os, re, time, codecs, cgi, string, urllib, time

from wsgiref.util import application_uri
from wsgiref.headers import Headers

from datetime import datetime
from traceback import format_tb
import urlparse
from webob import Request
import tempita

from utilities import *

import logging
log = logging.getLogger()


__author__ = 'Andrea Peltrin and Rui Carmo'
__version__ = (0, 6, 0, '')
__license__ = 'MIT'

VERSION_STRING = '%d.%d.%d%s' % __version__

DEBUG = False

ENCODING = 'utf-8'
CONFIGURATION_PATH = './coldsweat.ini'


##@@TODO Load up config file 
#config = load_config(CONFIGURATION_PATH)

#@@FIXME Use httplib.responses http://docs.python.org/2/library/httplib.html

HTTP_OK = '200 OK'
HTTP_NOT_FOUND = '404 Not Found'
HTTP_SEE_OTHER = '303 See Other'
# HTTP_MOVED_PERMANENTLY = '301 Moved Permanently'
HTTP_INTERNAL_SERVER_ERROR = '500 Internal Server Error'
HTTP_FORBIDDEN = '403 Forbidden'
HTTP_UNAUTHORIZED = '401 Unauthorized'


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
 
 
# ------------------------------------------------------
# Response
# ------------------------------------------------------

URI_MAP = []
    
# Decorator
def view(pattern='^$', method='GET'):    
    
    def _(handler):         
        URI_MAP.append((re.compile(pattern, re.U), method.upper(), handler))
        return handler   
    return _   
    
def dispatch_request(environ, start_response):

    request = Request(environ) 

    output_headers = Headers([('Content-Type', 'text/html; charset=%s' % ENCODING)])

    template_symbols = {
        'base_uri': get_base_uri(environ), 
        'encoding': ENCODING,
        'version_string': VERSION_STRING
    }
    
    # Setup common template symbols
    filler = fill_template_namespace(**template_symbols)

    try:
        path_info = request.path_info
    except KeyError:
        path_info = ''
    
    def find_view():
    
        for re, method, handler in URI_MAP:        
            match = re.match(path_info)
            if match and (method == request.method):                    
                return handler, match.groups()
    
        raise NotFoundError  
    
    def response(lines):
        for line in lines:
            yield encode(line)

    try:                    
        handler, args = find_view()
                   
        if not args:
            args = ()

        status, headers, body = handler(request, filler, *args)

        for name, value in headers:
            if name == 'Content-Type':
                output_headers[name] = value # Replace default value
            else:
                output_headers.add_header(name, value)

    except NotFoundError, exc:     
        status = str(exc)
        if exc.body:
            message = exc.body
        else:
            message = u'Resource <i>%s</i> could not be found on this server.' % path_info
                    
        body = make_page('404.html', filler, {'message': message})

    #output_headers['Content-Length'] = str(len(body))

    #@@NOTE: Looks wrong to me. However, WSGI handlers.py uses StringType 
    #  instead of str while asserting for k and v types
    start_response(status, [(str(k), str(v)) for k, v in output_headers.items()])    
    #start_response(status, str(output_headers))    

    return response([body])


# ------------------------------------------------------
# Misc. utilities
# ------------------------------------------------------

def get_base_uri(environ):
    _, filename = os.path.split(environ.get('SCRIPT_FILENAME', ''))    
    return application_uri(environ).replace('/%s' % filename, '')
    
class HTTPError(Exception):
    def __init__(self, status, headers=[], body=u''):
        self.headers = headers
        self.body = body
        super(HTTPError, self).__init__(status)

class NotFoundError(HTTPError):
    def __init__(self, headers=[], body=u''): 
        super(NotFoundError, self).__init__(HTTP_NOT_FOUND, headers, body)
                

def redirect_to(uri, headers=None):    
    output_headers = [('Location', uri)]
    if headers: 
        output_headers.extend(headers)
    return HTTP_SEE_OTHER, output_headers, u''
 

def sanitize(value, escape=True, truncate=30):     
    if truncate:
        value = value[:truncate]
    
    return escape_html(value) if escape else value

   
# ------------------------------------------------------
# Templates
# ------------------------------------------------------

def fill_template_namespace(**kwargs):            
    d = kwargs.copy()
    def _(t, **kwargs):
        d.update(kwargs)        
        return t.substitute(d)
    return _


def get_template(filename, from_template):
    """
    Load an inherited template
    """
    return tempita.Template.from_filename(os.path.join(BASE_DIR, 'templates', filename))
        
def fill_template(source, **kwargs):    
    t = tempita.Template(source, get_template=get_template)    
    return t.substitute(kwargs)


def load_template(filename):            
    return tempita.Template.from_filename(os.path.join(BASE_DIR, 'templates', filename), get_template=get_template)


def make_page(filename, filler, symbols):

    d = {
         'page_title': symbols.get('page_title', 'Coldsweat')        
    }
                           
    d.update(symbols)            
    body = filler(load_template(filename), **d) 

    return body


# ------------------------------------------------------
# Exception middleware
# ------------------------------------------------------

class ExceptionMiddleware(object):
    '''
    Sends out an exception traceback if something goes wrong.
                
    See: http://lucumr.pocoo.org/2007/5/21/getting-started-with-wsgi/
    '''
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        """
        Call the application can catch exceptions.
        """
        appiter = None
        # Just call the application and send the output back
        # unchanged but catch exceptions
        try:
            appiter = self.app(environ, start_response)
            for item in appiter:
                yield item
        # If an exception occours we get the exception information
        # and prepare a traceback we can render
        except:
            type, value, tb = sys.exc_info()
            traceback = ['Traceback (most recent call last):']
            traceback += format_tb(tb)
            traceback.append('%s: %s' % (type.__name__, value))
            # We might have not a stated response by now. Try
            # to start one with the status code 500 or ignore an
            # raised exception if the application already started one
            try:
                start_response(HTTP_INTERNAL_SERVER_ERROR, [
                               ('Content-Type', 'text/plain')])
            except Exception:
                pass
            yield '\n'.join(traceback)

        # Wsgi applications might have a close function. If it exists
        # it *must* be called
        if hasattr(self.app, 'close'):
            self.app.close()

# Install ExceptionMiddleware
dispatch_request = ExceptionMiddleware(dispatch_request)            


# ------------------------------------------------------
# All set, import views
# ------------------------------------------------------

# Fever API
import fever

# Web views
import views

