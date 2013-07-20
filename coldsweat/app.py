# -*- coding: utf-8 -*-
'''
Description: Web app machinery

Copyright (c) 2013— Andrea Peltrin
Portions are copyright (c) 2013 Rui Carmo
License: MIT (see LICENSE.md for details)
'''
import sys, os, re

from webob import Request, Response
from webob.exc import *

from utilities import *
from models import connect, close

from coldsweat import log, config, installation_dir

SESSION_KEY = 'com.passiomatic.coldsweat.session'
#TEMPLATE_DIR = os.path.join(installation_dir, 'coldsweat/templates')
# Figure out static dir, if given
STATIC_URL = config.get('web', 'static_url') if config.has_option('web', 'static_url') else ''

# ------------------------------------------------------
# Decorators
# ------------------------------------------------------

def on(pattern, http_method):    
    def _(handler):         
        handler.pattern = re.compile(pattern, re.U)
        handler.http_method = http_method.upper()
        return handler       
    return _  

def GET(pattern='^/$'):    
    return on(pattern, 'get')  

def POST(pattern='^/$'):    
    return on(pattern, 'post')  

# ------------------------------------------------------
# Base WSGI app
# ------------------------------------------------------

    
class WSGIApp(object):

#     def __init__(self):
#         pass
    
    def __call__(self, environ, start_response):
        connect()
        
        self.request = Request(environ)
        
        handler, args = self.find_handler()
        if not handler:
            raise HTTPNotFound('No such view %s' % self.request.path_info)  
        if not args:
            args = ()        
            
        response = handler(self, self.request, *args)        
        if not response:
            response = Response()

# Base WSGI app shoud be session agnostic
#         if SESSION_KEY in environ:
#             self.session = environ[SESSION_KEY]
#         else:
#             self.session = {} # Fail soft

        return response(environ, start_response)
    
    def find_handler(self):
    
        try:
            self.request.path_info
        except KeyError:
            self.request.path_info = '/'
                       
        for name, handler in self.__class__.__dict__.items():        
            if not hasattr(handler, 'pattern'):
                continue

            match = handler.pattern.match(self.request.path_info)            
            if match and handler.http_method == self.request.method:                    
                return handler, match.groups()
    
        return None, None


    def close(self):
        close()
 
 
# ------------------------------------------------------
# Exception middleware
# ------------------------------------------------------

class ExceptionMiddleware(object):
    '''
    WSGI middleware which sends out an exception traceback if something goes wrong.                
    See: http://lucumr.pocoo.org/2007/5/21/getting-started-with-wsgi/
    '''
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        """
        Call the application and catch exceptions.
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
                
        # Wsgi applications might have a close function. 
        # If it exists it *must* be called
        if hasattr(self.app, 'close'):
            self.app.close()



# def setup_app():
#     '''
#     Install middleware and return app
#     '''
#     #return ExceptionMiddleware(SessionMiddleware(ColdsweatApp(), session_key=SESSION_KEY))
#     return ExceptionMiddleware(ColdsweatApp())

