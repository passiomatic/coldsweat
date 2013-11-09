# -*- coding: utf-8 -*-
'''
Description: Web app machinery

Copyright (c) 2013— Andrea Peltrin
Portions are copyright (c) 2013 Rui Carmo
License: MIT (see LICENSE.md for details)
'''
import sys, os, re
from traceback import format_tb

from webob import Request, Response
from webob.exc import *

from utilities import *
from models import connect
from coldsweat import log, config, installation_dir

# Figure out static dir, if given
STATIC_URL = config.get('web', 'static_url') if config.has_option('web', 'static_url') else ''

# ------------------------------------------------------
# Decorators
# ------------------------------------------------------

def on(pattern, http_methods):    
    def wrapper(handler):         
        handler.pattern = re.compile(pattern, re.U)
        handler.http_methods = [m.upper() for m in http_methods]
        return handler         
    return wrapper  

def GET(pattern='^/$'):    
    return on(pattern, ('get', ))  

def POST(pattern='^/$'):    
    return on(pattern, ('post', ))  

# Handler for both GET and POST requests
def form(pattern='^/$'):    
    return on(pattern, ('get', 'post'))  

# ------------------------------------------------------
# Base WSGI app
# ------------------------------------------------------

    
class WSGIApp(object):

    redirect_exceptions = (HTTPTemporaryRedirect, HTTPMovedPermanently, HTTPSeeOther)

    def __call__(self, environ, start_response):
        
        self.request = Request(environ)
        
        handler, args = self.find_handler()
        if not handler:
            raise HTTPNotFound('No handler defined for %s (%s)' % (self.request.path_info, self.request.method))  
        if not args:
            args = ()        

        # Prepare database connection
        connect()
        
        response = handler(self, self.request, *args)
        if not response:
            response = Response() # Provide an empty response

# Base WSGI app shoud be session agnostic
#         self.session = dict()
#
#         if SESSION_KEY in environ:
#             self.session = environ[SESSION_KEY]
#         else:
#             self.session = {} # Fail soft

        #log.debug('Response for call %s is %s' % (self.request.path_info, type(response)))
        return response(environ, start_response)
    
    def find_handler(self):
    
        # Sanity check
        try:
            self.request.path_info
        except KeyError:
            self.request.path_info = ''
                       
        for name, handler in self.__class__.__dict__.items():        
            if not hasattr(handler, 'pattern'):
                continue

            match = handler.pattern.match(self.request.path_info)            
            if match and self.request.method in handler.http_methods:                    
                return handler, match.groups()
    
        return None, None

 
# ------------------------------------------------------
# Exception middleware
# ------------------------------------------------------

class ExceptionMiddleware(object):
    '''
    WSGI middleware which sends out an exception traceback 
      if something goes wrong. See: http://bit.ly/hQd5b1
    '''
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        """
        Call the application and catch exceptions.
        """
        app_iter = None

        # Just call the application and send the output back
        #   unchanged and catch relevant HTTP exceptions
        try:
            app_iter = self.app(environ, start_response)
        except (HTTPClientError, HTTPRedirection), exc:        
            app_iter = exc(environ, start_response)            
        # If an exception occours we get the exception information
        #   and prepare a traceback we can render
        except Exception:        
            exc_type, exc_value, tb = sys.exc_info()
            traceback = ['Traceback (most recent call last):']
            traceback += format_tb(tb)
            traceback.append('%s: %s' % (exc_type.__name__, exc_value))
            # We might have not a stated response by now. Try to  
            #   start one with the status code 500 or ignore any
            #   raised exception if the application already
            #   started one            
            try:
                start_response('500 Internal Server Error', [
                               ('Content-Type', 'text/plain')])
            except Exception:
                pass
            
            traceback = '\n'.join(traceback)            
            log.error(traceback)
                        
            yield traceback
        
        for item in app_iter:
            yield item

        # Returned iterable might have a close function. 
        #   If it exists it *must* be called
        if hasattr(app_iter, 'close'):
            app_iter.close()


# ------------------------------------------------------
# Set up WSGI app
# ------------------------------------------------------

from fever import fever_app
from frontend import frontend_app
from cascade import Cascade

def setup_app():
    return ExceptionMiddleware(Cascade([fever_app, frontend_app]))

app = setup_app()
