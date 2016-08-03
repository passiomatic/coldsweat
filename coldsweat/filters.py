# -*- coding: utf-8 -*-
"""
Description: Template filters

Copyright (c) 2013—2016 Andrea Peltrin
License: MIT (see LICENSE for details)
"""
import re, cgi, urllib, urlparse
from webob.exc import status_map
import utilities

__all__ = []

def filter(filtername):        
    '''
    Define a filter
    '''
    def _(handler):
        handler.name = filtername
        __all__.append(handler.__name__)
        return handler
    return _
    
# ------------------------------------------------------
# Filters
# ------------------------------------------------------

@filter('html')
def escape_html(value):     
    if value:    
        return cgi.escape(value, quote=True)
    return ''

@filter('url')
def escape_url(value):     
    if value:
        return urllib.quote(utilities.encode(value))
    return ''

@filter('friendly_url')
def friendly_url(value):
    if value:
        u = urlparse.urlsplit(value)
        return u.netloc 
    return ''

@filter('capitalize')
def capitalize(value):
    if value:        
        return value.capitalize()
    return ''

@filter('length')
def length(value):
    if value:
        return len(list(value))
    return 0
        
@filter('datetime')
def datetime(value):
    if value:        
        return utilities.format_datetime(value)
    return '—'

@filter('iso_datetime')
def iso_datetime(value):
    if value:        
        return utilities.format_iso_datetime(value)
    return ''  

@filter('date')
def date(value):
    if value:        
        return utilities.format_date(value)
    return '—'

@filter('since')
def datetime_since(value):                                
    if value:
        return utilities.datetime_since(value)
    return '—' 

@filter('since_today')
def datetime_since_today(value):
    if value:
        return utilities.datetime_since_today(value)
    return '—' 

@filter('epoch')
def epoch(value):                                
    if value:
        return utilities.datetime_as_epoch(value)
    return '—' 

@filter('status_title')
def status_title(code):
    title = 'Unknown (%s)' % code
    try:
        return status_map[code].title
    except KeyError:
        pass 
    return title
    
@filter('alert')
def alert(message):
    if not message:
        return ''        
    try: 
        klass, text = message.split(u' ', 1)
    except ValueError:
        return text
    return u'<div class="alert alert--%s">%s</div>' % (klass.lower(), text)
    
def run_tests():
    
    #t = datetime.utcnow()        
            
    assert friendly_url('http://example.org/feed.xml') == 'example.org'
    assert friendly_url(None) == ''
    
if __name__ == '__main__':
    run_tests()
