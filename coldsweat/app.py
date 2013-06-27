# -*- coding: utf-8 -*-
'''
Coldsweat - Web app machinery

Copyright (c) 2013— Andrea Peltrin
Portions are copyright (c) 2013 Rui Carmo
License: MIT (see LICENSE.md for details)
'''
import sys, os, re, time, cgi

from webob import Request, Response
from webob.exc import *
import tempita

from utilities import *
from coldsweat import log, config, installation_dir, VERSION_STRING
#from models import connect


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

def template(filename):

    def wrapped(handler): 

        def _wrapped(ctx, *args):

            if ctx.request.cookies.get('alert_message'):
                message = ctx.request.cookies['alert_message']
            else:
                message = ''
            
            # Global symbols
            kwargs = {
                'alert_message': render_message(message),                
                'version_string': VERSION_STRING,
                'ctx': ctx,
                'request': ctx.request,
                'response': ctx.response,
                'static_url': ctx.static_url,
            }
            
            d = handler(ctx, *args)
            if d:
                kwargs.update(d)

            ctx.response.body = render_template(filename, **kwargs)

            # Delete alert_message cookie, if any
            if message:
                ctx.response.delete_cookie('alert_message')
                                    
        return _wrapped

    return wrapped

# ------------------------------------------------------
# Templates
# ------------------------------------------------------

def render_template(filename, **kwargs):            

    def _(filename, from_template):
        """
        Load an inherited template
        """
        return tempita.Template.from_filename(os.path.join(TEMPLATE_DIR, filename))

    return tempita.Template.from_filename(os.path.join(TEMPLATE_DIR, filename), get_template=_).substitute(**kwargs)

 
@template('404.html')
def http_not_found(ctx):
    pass    

    
# def dispatch_request(environ, start_response):
# 
#     request     = Request(environ) 
#     response    = Response(charset='utf-8')
#     
#     request.base_url = fix_application_url(request)
# 
#     output_headers = Headers([('Content-Type', 'text/html; charset=utf-8')])
# 
#     template_symbols = {
#         'base_url': request.base_url, #get_base_url(request), 
#         #'encoding': ENCODING,
#         'version_string': VERSION_STRING
#     }
#     
#     # Setup common template symbols
#     filler = fill_template_namespace(**template_symbols)
# 
#     try:
#         path_info = request.path_info
#     except KeyError:
#         path_info = ''
# 
#     def find_view():
#     
#         for re, method, handler in URI_MAP:        
#             match = re.match(path_info)
#             if match and (method == request.method):                    
#                 return handler, match.groups()
#     
#         raise NotFoundError  
#     
#     def response(lines):
#         for line in lines:
#             #yield encode(line)
#             yield line
# 
#     try:                    
#         handler, args = find_view()
#                    
#         if not args:
#             args = ()
# 
#         status, headers, body = handler(request, filler, *args)
# 
#         for name, value in headers:
#             if name == 'Content-Type':
#                 output_headers[name] = value # Replace default value
#             else:
#                 output_headers.add_header(name, value)
# 
#     except NotFoundError, exc:     
#         status = str(exc)
#         if exc.body:
#             message = exc.body
#         else:
#             message = u'Resource <i>%s</i> could not be found on this server.' % path_info
#                     
#         body = make_page('404.html', filler, {'message': message})
# 
#     #output_headers['Content-Length'] = str(len(body))
# 
#     #@@NOTE: Looks wrong to me. However, WSGI handlers.py uses StringType 
#     #  instead of str while asserting for k and v types
#     start_response(status, [(str(k), str(v)) for k, v in output_headers.items()])    
#     #start_response(status, str(output_headers))    
# 
#     return response([body])


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
            # to start one with the status code 500 or ignore an
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

