# -*- coding: utf-8 -*-
'''
Coldsweat - Web app machinery

Copyright (c) 2013— Andrea Peltrin
Portions are copyright (c) 2013 Rui Carmo
License: MIT (see LICENSE.md for details)
'''
import sys, os, re

from webob import Request, Response
from webob.exc import *
from tempita import Template #, HTMLTemplate 

from utilities import *
from coldsweat import log, config, installation_dir, VERSION_STRING

ENCODING = 'utf-8'
TEMPLATE_DIR = os.path.join(installation_dir, 'coldsweat/templates')
URI_MAP = []
    
class Context(object):
    def __init__(self, request, response, static_url):
        self.request = request
        self.response = response
        self.static_url = static_url
        

# See http://docs.webob.org/en/latest/wiki-example.html    
class ColdsweatApp(object):

    def __init__(self, static_url=None):    
        self.static_url = static_url

    def find_view(self, request):

        try:
            request.path_info
        except KeyError:
            request.path_info = ''
            
        if not request.path_info:
            # Requested by CGIHandler 
            request.path_info = '/'
                                        
        for re, method, view in URI_MAP:        
            match = re.match(request.path_info)
            if match and (method == request.method):                    
                return view, match.groups()
    
        raise HTTPNotFound('No such view %s' % request.path_info)  


    def __call__(self, environ, start_response):
 
        request = Request(environ)
        response = Response(content_type='text/html', charset=ENCODING)

        ctx = Context(request, response, self.static_url if self.static_url else request.application_url) 

        try:
            view, args = self.find_view(request)
            if not args:
                args = ()

            r = view(ctx, *args)
            if r:
                ctx.response = r    
#         except HTTPNotFound, exc:
#             ctx.response = http_not_found(ctx)
        except HTTPException, exc:
            # The exception object itself is a WSGI application/response
            ctx.response = exc

        return ctx.response(environ, start_response)


 
 
# ------------------------------------------------------
# Decorators
# ------------------------------------------------------

def view(pattern='^/$', method='GET'):    
    
    def wrapped(handler):         
        URI_MAP.append((re.compile(pattern, re.U), method.upper(), handler))
        return handler   
    
    return wrapped  

import json 
def template(filename, content_type='text/html'):

    def wrapped(handler): 

        def _wrapped(ctx, *args):

            if ctx.request.cookies.get('alert_message'):
                message = ctx.request.cookies['alert_message']
            else:
                message = ''
            
            # Global namespace
            namespace = {
                'request': ctx.request,
                'response': ctx.response,

                'static_url': ctx.static_url,
                'application_url': ctx.request.application_url,
                'alert_message': render_message(message),                

                # Filters 
                #'javascript': escape_javacript,
                'html': escape_html,
                'timestamp': timestamp(datetime.utcnow()),
            }
            
            # Allow override global namespace symbols
            d = handler(ctx, *args)
            if d: 
                namespace.update(d)
                
            ctx.response.body = render_template(filename, **namespace)
            ctx.response.content_type = content_type
            #ctx.response.charset=ENCODING

            # Delete alert_message cookie, if any
            if message:
                ctx.response.delete_cookie('alert_message')
                                    
        return _wrapped

    return wrapped

# ------------------------------------------------------
# Templates
# ------------------------------------------------------

def render_template(filename, **kwargs):            
    return Template.from_filename(os.path.join(TEMPLATE_DIR, filename)).substitute(**kwargs)

 
@template('404.html')
def http_not_found(ctx):
    pass    

    
# ------------------------------------------------------
# Misc. utilities
# ------------------------------------------------------
 
def set_message(response, message):
    response.set_cookie('alert_message', message)

def render_message(message):
    if not message:
        return ''
        
    try: 
        klass, text = message.split(u' ', 1)
    except ValueError:
        return text
    return u'<div class="alert alert--%s">%s</div>' % (klass.lower(), text)

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
        app_iter = None
        # Just call the application and send the output back
        # unchanged but catch exceptions
        try:
            app_iter = self.app(environ, start_response)
            for item in app_iter:
                yield item
        # If an exception occours we get the exception information
        # and prepare a traceback we can render
        except Exception:
            from traceback import format_tb

            type, value, tb = sys.exc_info()
            traceback = ['Traceback (most recent call last):']
            traceback += format_tb(tb)
            traceback.append('%s: %s' % (type.__name__, value))
            # We might have not a stated response by now. Try
            # to start one with the status code 500 or ignore any
            # raised exception if the application already started one            
            try:
                start_response('500 Internal Server Error', [
                               ('Content-Type', 'text/plain')])
            except Exception:
                pass
            
            traceback = '\n'.join(traceback)            
            log.error(traceback)
                        
            yield traceback

        # Wsgi applications might have a close function. If it exists
        # it *must* be called
        if hasattr(self.app, 'close'):
            self.app.close()

# ------------------------------------------------------
# All set, import views
# ------------------------------------------------------

# Fever API
import fever

# Web views
import views

