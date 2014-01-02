# -*- coding: utf-8 -*-
"""
Description: misc. utilities

Copyright (c) 2013— Andrea Peltrin
Portions are copyright (c) 2013 Rui Carmo
License: MIT (see LICENSE.md for details)
"""
import re, cgi, urllib, urlparse
from hashlib import md5, sha1
from calendar import timegm
from datetime import datetime
from tempita import HTMLTemplate
from webob.exc import status_map

def encode(value):
    return value.encode('utf-8', 'replace')
    
# --------------------
# Hash functions
# --------------------

def make_md5_hash(s):      
    return md5(encode(s)).hexdigest()

def make_sha1_hash(s):          
    return sha1(encode(s)).hexdigest()


# --------------------
# URL functions
# --------------------

# Lifted from https://github.com/django/django/blob/master/django/core/validators.py
RE_URL = re.compile(
    r'^https?://'  # http:// or https://
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
    r'localhost|'  # localhost...
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
    r'(?::\d+)?'  # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE)    
    #@@TODO: Add IPv6
    

def is_valid_url(value):
    return value and RE_URL.search(value)
    
# --------------------
# Date/time functions
# --------------------

# Weekday and month names for HTTP date/time formatting; always English!
_weekdayname = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_monthname = [None, # Dummy so we can use 1-based month numbers
              "Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
              
def format_datetime(value, comparsion_value=None):
    
    if not comparsion_value:    
        return value.strftime('%a, %d %b %H:%M UTC')
    
    delta = comparsion_value - value    
    if delta.days < 1:       
        if delta.seconds > 3600: 
            s = '%d hours ago' % (delta.seconds/60/60)
        elif 60 <= delta.seconds <= 3600: 
            s = '%d minutes ago' % (delta.seconds/60)
        else:
            s = 'Just now'
    else:
        s = '%d days ago' % delta.days

    return s

def format_http_datetime(value):
    """
    Format datetime to comply with RFC 1123 
    (ex.: Fri, 12 Feb 2010 16:23:03 GMT). 
    Assume GMT values
    """
    year, month, day, hh, mm, ss, wd, y, z = value.utctimetuple()
    return "%s, %02d %3s %4d %02d:%02d:%02d GMT" % (
        _weekdayname[wd], day, _monthname[month], year, hh, mm, ss
    )
       
def datetime_as_epoch(value):
    return int(timegm(value.utctimetuple()))

def tuple_as_datetime(value):
    return datetime.utcfromtimestamp(timegm(value))


# --------------------
# Teplate filters and utilities
# --------------------

def escape_html(value):     
    """
    Return value escaped as HTML string
    """
    return cgi.escape(value, quote=True)

def escape_url(value):     
    """
    Return value escaped as URL string
    """
    return urllib.quote(value)

def friendly_url(value):
    if value:
        u = urlparse.urlsplit(value)
        return u.netloc 
    else:
        return ''
    
    
# def escape_javacript(value):     
#     """
#     Return value escaped as a Javascript string
#     """
#     return json.dumps(value)

def datetime_since(utcnow):                                
    def _(value):
        if value:
            return format_datetime(value, utcnow)
        else:
            return '—' 
    return _

# def get_excerpt(value, truncate=200):     
#     """
#     Escape and truncate an HTML string
#     """
#     if truncate:
#         value = value[:truncate]
#     
#     return cgi.escape(value, quote=True)

def render_template(filename, namespace):                    
    return HTMLTemplate.from_filename(filename, namespace=namespace).substitute()

def get_status_title(code):
    title = 'Unknown (%s)' % code
    try:
        title = status_map[code].title
    except KeyError:
        pass 
    return title
    
# --------------------
# Misc.
# --------------------
    
class Struct(dict):
    """
    An object that recursively builds itself from a dict 
    and allows easy access to attributes
    """

    def __init__(self, obj):
        dict.__init__(self, obj)
        for k, v in obj.iteritems():
            if isinstance(v, dict):
                self.__dict__[k] = Struct(v)
            else:
                self.__dict__[k] = v

    def __getattr__(self, attr):
        try:
            return self.__dict__[attr]
        except KeyError:
            raise AttributeError(attr)
            
    def __setitem__(self, key, value):
        super(Struct, self).__setitem__(key, value)
        self.__dict__[key] = value

    def __setattr__(self, attr, value):
        self.__setitem__(attr, value)            

    
def run_tests():
    
    t = datetime.utcnow()        
    
    v = datetime(2013, 6, 25, 12, 0, 0)
    print format_datetime(v, t)    
    v = datetime(t.year, t.month, t.day, 12, 0, 0)
    print format_datetime(v, t)    
    v = datetime(t.year, t.month, t.day, t.hour, 0, 0)
    print format_datetime(v, t)    
    v = datetime(t.year, t.month, t.day, t.hour, t.minute, 0)
    print format_datetime(v, t)    
    
    print format_http_datetime(t)
     
    assert is_valid_url('https://example.com')          # OK
    assert is_valid_url('http://example.org/feed.xml')  # OK
    assert not is_valid_url('example.com')              # Fail

    assert friendly_url('http://example.org/feed.xml') == 'example.org'
    assert friendly_url(None) == ''
    
    #print get_excerpt('Some <script src="http://example.com/evil.js"></script> code.')
    
if __name__ == '__main__':
    run_tests()
