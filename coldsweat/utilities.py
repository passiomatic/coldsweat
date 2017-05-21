# -*- coding: utf-8 -*-
"""
Description: misc. utilities

Copyright (c) 2013—2016 Andrea Peltrin
Portions are copyright (c) 2013 Rui Carmo
License: MIT (see LICENSE for details)
"""
import os, sys, traceback, re, cgi, urllib, urlparse
from hashlib import md5, sha1
import base64
from calendar import timegm
from datetime import datetime, timedelta
from tempita import HTMLTemplate

# --------------------
# Dump utilities
# --------------------

def dump_obj(obj, output=sys.stdout, nested_level=0):
    """
    A generic method to recursively pretty print the object's attributes and values.
    """
    spacing = '   '
    if type(obj) == dict:
        print >> output, '%s{' % ((nested_level) * spacing)
        for k, v in obj.items():
            if hasattr(v, '__iter__'):
                print >> output, '%s%s:' % ((nested_level + 1) * spacing, k)
                dump_obj(v, output, nested_level + 1,)
            else:
                print >> output, '%s%s: %s' % ((nested_level + 1) * spacing, k, v)
        print >> output, '%s}' % (nested_level * spacing)
    elif type(obj) == list:
        print >> output, '%s[' % ((nested_level) * spacing)
        for v in obj:
            if hasattr(v, '__iter__'):
                dump_obj(v, output, nested_level + 1)
            else:
                print >> output, '%s%s' % ((nested_level + 1) * spacing, v)
        print >> output, '%s]' % ((nested_level) * spacing)
    else:
        print >> output, '%s%s' % (nested_level * spacing, obj)

def dump_environ(obj, output=sys.stdout):
    """
    Specialized method to dump the WSGI 'environ' dictionary. Useful to debug requests.
    Note all values are printed, however. To do that, use 'dump_obj' instead.
    """
    
    if type(obj) == dict:
        spacing = '   '
        print >> output, '{'
        if obj.has_key('SERVER_SOFTWARE'):
            print >> output, '%s%s: %s' % (spacing, 'SERVER', obj['SERVER_SOFTWARE'])
        if obj.has_key('GATEWAY_INTERFACE'):
            print >> output, '%s%s: %s' % (spacing, 'WSGI', obj['GATEWAY_INTERFACE'])
        if obj.has_key('wsgi.version'):
            print >> output, '%s%s: %s' % (spacing, 'WSGI_VERSION', obj['wsgi.version'])
        if obj.has_key('wsgi.url_scheme'):
            print >> output, '%s%s: %s' % (spacing, 'WSGI_URL_SCHEME', obj['wsgi.url_scheme'])
        if obj.has_key('SERVER_PROTOCOL'):
            print >> output, '%s%s: %s' % (spacing, 'PROTOCOL', obj['SERVER_PROTOCOL'])
        if obj.has_key('REQUEST_METHOD'):
            print >> output, '%s%s: %s' % (spacing, 'HTTP_REQUEST_METHOD', obj['REQUEST_METHOD'])
        if obj.has_key('REMOTE_ADDR'):
            print >> output, '%s%s: %s' % (spacing, 'REMOTE_ADDR', obj['REMOTE_ADDR'])
        if obj.has_key('SERVER_PORT'):
            print >> output, '%s%s: %s' % (spacing, 'SERVER_PORT', obj['SERVER_PORT'])
        if obj.has_key('HTTP_HOST'):
            print >> output, '%s%s: %s' % (spacing, 'HTTP_HOST', obj['HTTP_HOST'])
        if obj.has_key('HTTP_COOKIE'):
            print >> output, '%s%s: %s' % (spacing, 'HTTP_COOKIES', obj['HTTP_COOKIE'])
        if obj.has_key('HTTP_USER_AGENT'):
            print >> output, '%s%s: %s' % (spacing, 'HTTP_USER_AGENT', obj['HTTP_USER_AGENT'])
        if obj.has_key('HTTP_ACCEPT'):
            print >> output, '%s%s: %s' % (spacing, 'HTTP_ACCEPT', obj['HTTP_ACCEPT'])
        if obj.has_key('HTTP_ACCEPT_LANGUAGE'):
            print >> output, '%s%s: %s' % (spacing, 'HTTP_ACCEPT_LANGUAGE', obj['HTTP_ACCEPT_LANGUAGE'])
        if obj.has_key('HTTP_ACCEPT_ENCODING'):
            print >> output, '%s%s: %s' % (spacing, 'HTTP_ACCEPT_ENCODING', obj['HTTP_ACCEPT_ENCODING'])
        if obj.has_key('HTTP_CONNECTION'):
            print >> output, '%s%s: %s' % (spacing, 'HTTP_CONNECTION', obj['HTTP_CONNECTION'])
        if obj.has_key('CONTENT_TYPE'):
            print >> output, '%s%s: %s' % (spacing, 'CONTENT_TYPE', obj['CONTENT_TYPE'])
        if obj.has_key('PATH_INFO'):
            print >> output, '%s%s: %s' % (spacing, 'PATH_INFO', obj['PATH_INFO'])
        if obj.has_key('QUERY_STRING'):
            print >> output, '%s%s: %s' % (spacing, 'QUERY_STRING', obj['QUERY_STRING'])
        if obj.has_key('HTTP_DNT'):
            print >> output, '%s%s: %s' % (spacing, 'HTTP_DNT', obj['HTTP_DNT'])
        if obj.has_key('HTTP_UPGRADE_INSECURE_REQUESTS'):
            print >> output, '%s%s: %s' % (spacing, 'HTTP_UPGRADE_INSECURE_REQUESTS', obj['HTTP_UPGRADE_INSECURE_REQUESTS'])
        if obj.has_key('CONTENT_LENGTH'):
            print >> output, '%s%s: %s' % (spacing, 'CONTENT_LENGTH', obj['CONTENT_LENGTH'])
        if obj.has_key('SCRIPT_NAME'):
            print >> output, '%s%s: %s' % (spacing, 'SCRIPT_NAME', obj['SCRIPT_NAME'])
        print >> output, '}'
    else:
        raise ValueError("the given object is not a dictionary")


# --------------------
# String utilities
# --------------------

def encode(value):
    return value.encode('utf-8', 'replace')    

def truncate(value, max_length):
    """
    Return a truncated string for value if value length is > max_length
    """
    if len(value) < max_length:
        return value
    return value[:max_length-1] + u'…'   

def make_data_uri(content_type, data):
    """
    Return data as a data:URI scheme
    """
    return "data:%s;base64,%s" % (content_type, base64.standard_b64encode(data))


# --------------------
# Hash functions
# --------------------

def make_md5_hash(s):      
    return md5(encode(s)).hexdigest()

def make_sha1_hash(s):          
    return sha1(encode(s)).hexdigest()

def make_nonce():
    try:
        nonce = os.urandom(16)
    except NotImplementedError: 
        # urandom might not be available on certain platforms
        nonce = datetime.now().isoformat()
    return nonce.encode('base64')
            
# --------------------
# Date/time functions
# --------------------

def datetime_as_epoch(value):
    return int(timegm(value.utctimetuple()))

def tuple_as_datetime(value):
    return datetime.utcfromtimestamp(timegm(value))

# Weekday and month names for HTTP date/time formatting; always English!
_weekdayname = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_monthname = [None, # Dummy so we can use 1-based month numbers
              "Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

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

def format_iso_datetime(value):
    # Unlike datetime.isoformat() assume UTC 
    return format_datetime(value, format='%Y-%m-%dT%H:%M:%SZ')
           
def format_datetime(value, format='%a, %b %d at %H:%M'):
    return value.strftime(format)

def format_date(value):
    return format_datetime(value, '%b %d, %Y')

def datetime_since(value, comparison_value=None, default="just now"):
    """
    Returns string representing "time since" e.g.
    3 days ago, 5 hours ago etc.
    
    From http://flask.pocoo.org/snippets/33/
    """

    comparison_value = comparison_value or datetime.utcnow()
    diff = comparison_value - value
    
    periods = (
        (diff.days / 365, "year", "years"),
        (diff.days / 30, "month", "months"),
        (diff.days / 7, "week", "weeks"),
        (diff.days, "day", "days"),
        (diff.seconds / 3600, "hour", "hours"),
        (diff.seconds / 60, "minute", "minutes"),
        (diff.seconds, "second", "seconds"),
    )

    for period, singular, plural in periods:        
        if period:
            return "%d %s ago" % (period, singular if period == 1 else plural)

    return default

def datetime_since_today(value, comparison_value=None):
    """
    Returns string representing "date since" e.g.
    today, yesterday and Wed, Jan 29
    """

    comparison_value = comparison_value or datetime.utcnow()    
    delta = comparison_value - value    
    if delta.days == 0:       
        return 'today'
    elif delta.days == 1: 
        return 'yesterday'
    
    # Earlier date
    return format_date(value)
    
    
# --------------------
# Misc.
# --------------------

# def render_template(filename, namespace):                    
#     return HTMLTemplate.from_filename(filename, namespace=namespace).substitute()

def render_template(filename, namespace, filters_module=None):                    
    # Install template filters if given
    if filters_module:
        filters_namespace = {}
        for name in filters_module.__all__:
            filter = getattr(filters_module, name)
            filters_namespace[filter.name] = filter
        # @@HACK Remove conflicting filter with HTMLTemplate
        del filters_namespace['html'] 
        # Update namespace, possibly overriding names
        namespace.update(filters_namespace)
    return HTMLTemplate.from_filename(filename, namespace=namespace).substitute()
        
class Struct(dict):
    """
    An object that recursively builds itself from a dict 
    and allows easy access to attributes
    """

    def __init__(self, d=None):
        d = d or {}
        super(Struct, self).__init__(d)
        for k, v in d.items():
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
    assert truncate(u'Lorèm ipsum dolor sit ame', 10) == u'Lorèm ips…'
    
if __name__ == '__main__':
    run_tests()
