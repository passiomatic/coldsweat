# -*- coding: utf-8 -*-
"""
Description: misc. utilities

Copyright (c) 2013— Andrea Peltrin
Portions are copyright (c) 2013 Rui Carmo
License: MIT (see LICENSE.md for details)
"""

from hashlib import md5, sha1
import time, timeformat, cgi


DEFAULT_ENCODING = 'utf-8'

def encode(value, encoding=DEFAULT_ENCODING):
    return value.encode(encoding, 'replace')

def decode(value, encoding=DEFAULT_ENCODING):  
    return unicode(value, encoding, 'replace')        

# --------------------
# Hash functions
# --------------------

def make_md5_hash(s):      
    return md5(encode(s)).hexdigest()

def make_sha1_hash(s):          
    return sha1(encode(s)).hexdigest()

# --------------------
# Format date/times
# --------------------

def format_datetime(seconds, short=True):    
    return timeformat.format(short and '%b[SHORT] %d, %Y' or '%b[SHORT] %d, %Y at %H:%M', 
        time.gmtime(seconds), utctime=True)

def format_iso_datetime(seconds):        
    return timeformat.format(u'%Y-%m-%dT%H:%M:%S%z', 
        time.gmtime(seconds), utctime=True)

# def format_log_datetime(datetime):
#     return timeformat.format(u'%d/%b[SHORT]/%Y:%H:%M:%S %T', 
#         datetime.timetuple(), utctime=True)

def format_http_datetime(datetime):        
    return timeformat.format(u'%a[SHORT], %d %b[SHORT] %Y %H:%M:%S %Z', 
        datetime.utctimetuple(), utctime=True)

# --------------------
# Escape functions
# --------------------

def escape_html(s):
    return cgi.escape(s, quote=True)

# def escape_url(value):
#     return urllib.quote(value)


# --------------------
# Misc
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
    
    t = time.time()
    
    print format_datetime(t)
    print format_iso_datetime(t)
    print format_http_datetime(t)
    print escape_html('Some <script src="http://example.com/evil.js"></script> code.')
    
if __name__ == '__main__':
    run_tests()
