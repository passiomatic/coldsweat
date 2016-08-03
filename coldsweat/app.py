# -*- coding: utf-8 -*-
'''
Description: Web app machinery

Copyright (c) 2013—2016 Andrea Peltrin
Portions are copyright (c) 2013 Rui Carmo
License: MIT (see LICENSE for details)
'''
import sys, os, re
from traceback import format_tb

from webob import Request, Response
from webob.exc import *

from utilities import *
from coldsweat import *

__all__ = [
    'GET',
    'POST',
    'form',
    'WSGIApp',
    'ExceptionMiddleware',
    'setup_app'
]

# ------------------------------------------------------
# Decorators
# ------------------------------------------------------

ROUTES = []

def on(pattern, http_methods):    
    def wrapper(handler):         
        route = re.compile(pattern, re.U), http_methods, handler.__name__
        ROUTES.append(route)
        return handler         
    return wrapper
        
def GET(pattern):    
    return on(pattern, ('GET', ))  

def POST(pattern):    
    return on(pattern, ('POST', ))  

# Handler for both GET and POST requests
def form(pattern):    
    return on(pattern, ('GET', 'POST'))  



# ------------------------------------------------------
# Base WSGI app
# ------------------------------------------------------

    
class WSGIApp(object):

    def __call__(self, environ, start_response):
        
        request = Request(environ)
        
        handler, args = self._find_handler(request)
        if not handler:
            raise HTTPNotFound('No handler defined for %s (%s)' % (request.path_info, request.method))  
        if not args:
            args = ()        
                            
        # Save request object for handlers
        self.request            = request
        self.application_url    = request.application_url
        
        response = handler(*args)
        if not response:
            response = Response() # Provide an empty response

        return response(environ, start_response)
    
    def _find_handler(self, request):

        # Sanity check
        try:
            request.path_info
        except KeyError:
            request.path_info = '' #@@TODO add / ? 

        for pattern, http_methods, name in ROUTES:
            match = pattern.match(request.path_info)        
            if match and request.method in http_methods:                    
                try:
                    return getattr(self, name), match.groups()
                except AttributeError:
                    break # path_info matches, but app does not

        # No match found
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
            logger.error(traceback)
                        
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

def setup_app():    
    # Postpone import to avoid circular dependencies
    import fever, frontend, cascade
    return ExceptionMiddleware(cascade.Cascade([fever.setup_app(), frontend.setup_app()]))
