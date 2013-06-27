# -*- coding: utf-8 -*-
"""
Description: misc. utilities

Copyright (c) 2013— Andrea Peltrin
Portions are copyright (c) 2013 Rui Carmo
License: MIT (see LICENSE.md for details)
"""

from hashlib import md5, sha1
from calendar import timegm
from datetime import datetime
import cgi

DEFAULT_ENCODING = 'utf-8'

def encode(value):
    return value.encode(DEFAULT_ENCODING, 'replace')

def decode(value):  
    return unicode(value, DEFAULT_ENCODING, 'replace')        

# --------------------
# Hash functions
# --------------------

def make_md5_hash(s):      
    return md5(encode(s)).hexdigest()

def make_sha1_hash(s):          
    return sha1(encode(s)).hexdigest()

# --------------------
# Date/time functions
# --------------------


# def format_iso_datetime(seconds):        
#     return timeformat.format(u'%Y-%m-%dT%H:%M:%S%z', 
#         time.gmtime(seconds), utctime=True)

# def format_http_datetime(value):        
#     return timeformat.format(u'%a[SHORT], %d %b[SHORT] %Y %H:%M:%S %z', 
#         value.utctimetuple(), utctime=True)

def format_http_datetime(value):
    """
    Format datetime to comply with RFC 1123 
    (ex.: Fri, 12 Feb 2010 16:23:03 GMT). 
    Assume GMT values
    """
    #@@FIXME: what if locale isn't en?
    return value.strftime(u'%a, %d %b %Y %H:%M:%S GMT')

def datetime_as_epoch(value):
    return int(timegm(value.utctimetuple()))
    
def tuple_as_datetime(value):
    return datetime.utcfromtimestamp(timegm(value))
   
# --------------------
# Misc
# --------------------

def get_excerpt(value, truncate=200):     
    """
    Escape and truncate an HTML string
    """
    if truncate:
        value = value[:truncate]
    
    return cgi.escape(value, quote=True)
    
    
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
    
    print format_http_datetime(t)
    print get_excerpt('Some <script src="http://example.com/evil.js"></script> code.')
    
if __name__ == '__main__':
    run_tests()
