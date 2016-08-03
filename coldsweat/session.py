# -*- coding: utf-8 -*-
"""
Description: web session functions and classes

Copyright (c) 2013—2016 Andrea Peltrin
Copyright (c) 2006 L. C. Rees
Copyright (c) 2005 Allan Saddi <allan@saddi.com>
Copyright (c) 2005, the Lawrence Journal-World

All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:

 1. Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.
 2. Redistributions in binary form must reproduce the above copyright
    notice, this list of conditions and the following disclaimer in the
    documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
SUCH DAMAGE.
"""

import sys, os, string, threading, atexit, random, weakref
from datetime import datetime, timedelta
from Cookie import SimpleCookie

from utilities import make_sha1_hash
from models import Session, connect, close
from coldsweat import logger

__all__ = [
    'SessionMiddleware',
]

SESSION_TIMEOUT = 60*60*24*30 # 1 month

def synchronized(func):
    def wrapper(self, *__args, **__kw):
        self._lock.acquire()
        try:
            return func(self, *__args, **__kw)
        finally:
            self._lock.release()
    wrapper.__name__ = func.__name__
    wrapper.__dict__ = func.__dict__
    wrapper.__doc__ = func.__doc__
    return wrapper


class SessionMiddleware(object):
    '''
    WSGI middleware that adds a session service in a cookie
    '''

    def __init__(self, app, **kwargs):
        self.app = app
        self.kwargs = kwargs # Pass everything else to SessionManager

    def __call__(self, environ, start_response):
        connect()
        
        # New session manager instance each time
        manager = SessionManager(environ, **self.kwargs)
        # Add a session object to wrapped app        
        self.app.session = manager.session

        # Initial response to a cookie session
        def initial_response(environ, start_response):
            def session_response(status, headers, exc_info=None):
                manager.set_cookie(headers)
                return start_response(status, headers, exc_info)
            return self.app(environ, session_response)

        try:
            # Return initial response if new or session id is random
            if manager.is_new: 
                return initial_response(environ, start_response)
            return self.app(environ, start_response)
        # Always close session
        finally:
            manager.close()

class SessionManager(object):
 
    def __init__(self, environ, fieldname, path='/'):   
        self._cache = SessionCache()
        self._fieldname = fieldname
        self._path = path
        
        self.session = self._sid = None
        self.is_new = False
        
        self._get(environ)

    def _get(self, environ):  
        '''
        Attempt to associate with an existing session
        '''
        self._from_cookie(environ)
        if self.session is None:
            self._sid, self.session = self._cache.create()
            self.is_new = True

    def close(self):
        '''
        Checks session back into session cache
        '''
        # Check the session back in and get rid of our reference.
        self._cache.checkin(self._sid, self.session)
        self.session = None

    # Cookie utilities

    def set_cookie(self, headers):
        '''
        Sets a session cookie header if needed
        '''
        cookie, name = SimpleCookie(), self._fieldname
        cookie[name], cookie[name]['path'],  cookie[name]['max-age'] = self._sid, self._path, SESSION_TIMEOUT
        headers.append(('Set-Cookie', cookie[name].OutputString()))

    def delete_cookie(self, headers):
        pass

    def _from_cookie(self, environ): 
        '''
        Attempt to load the associated session using the identifier from the cookie
        '''
        #@@TODO: Use Webob.request
        
        cookie = SimpleCookie(environ.get('HTTP_COOKIE'))
        morsel = cookie.get(self._fieldname, None)
        if morsel:
            self._sid, self.session = self._cache.checkout(morsel.value)
            cookie_sid = morsel.value
            if cookie_sid != self._sid: 
                self.is_new = True


def _shutdown(ref):
    cache = ref()
    if cache:
        cache.shutdown()
            

class SessionCache(object):
    '''
    You first acquire a session by calling create() or checkout(). After 
    using the session, you must call checkin(). You must not keep references 
    to sessions outside of a check in/check out block. Always obtain a fresh 
    reference
    '''
    # Would be nice if len(idchars) were some power of 2
    idchars = '-_'.join([string.digits, string.ascii_letters])
    length = 64

    def __init__(self, is_random=False):
        self._lock = threading.Condition()
        self.checkedout, self._closed  = dict(), False
        # Sets if session id is random on every access or not
        self.is_random = is_random
        self._secret = ''.join(self.idchars[ord(c) % len(self.idchars)]
            for c in os.urandom(self.length))
        # Ensure shutdown is called.
        atexit.register(_shutdown, weakref.ref(self))


    def __del__(self):
        self.shutdown()

    # Public interface

    @synchronized
    def create(self):
        '''
        Create a new session with a unique identifier.

        The newly-created session should eventually be released by
        a call to checkin()
        '''
        sid, value = self.get_new_id(), dict()
        set_session(sid, value)
        self.checkedout[sid] = value
        return sid, value

    @synchronized
    def checkout(self, sid):
        '''
        Checks out a session for use. Returns the session if it exists,
        otherwise returns None. If this call succeeds, the session
        will be touch()'ed and locked from use by other threads/processes.
        Therefore, it should eventually be released by a call to
        checkin()
        '''
        # If we know it's already checked out, block.
        while sid in self.checkedout:
            self._lock.wait()
        
        session = get_session(sid)
        if session:
            # Randomize session id if requested and remove old session id
            if self.is_random:
                delete_session(sid)
                sid = self.get_new_id()
            # Put in checkout
            self.checkedout[sid] = session.value
            return sid, session.value

        return None, None

    @synchronized
    def checkin(self, sid, value):
        '''
        Release the session for use by other threads/processes
        '''
        del self.checkedout[sid]
        set_session(sid, value)
        self._lock.notify()

    @synchronized
    def shutdown(self):
        '''
        Clean up outstanding sessions
        '''
        if not self._closed:
            # Save or delete any sessions that are still out there.
            for sid, value in self.checkedout.items():
                set_session(sid, value)
            self.checkedout.clear()
            #self.cache._cull()
            self._closed = True        

    # Utilities

    def get_new_id(self):
        '''
        Returns a session key that is not being used
        '''
        sid = None
        for _ in xrange(10000):
            a = random.randint(0, sys.maxint-1)
            b = random.randint(0, sys.maxint-1)            
            sid = make_sha1_hash('%s%s%s' % (a, b, self._secret))
            # Dupe? 
            if not get_session(sid):
                break
        return sid
        
# --------------------------------------
# Model interface 
# --------------------------------------

def get_session(sid, default=None):
    try:
        session = Session.get(Session.key==sid)
    except Session.DoesNotExist:
        return default
    
    # Expired?
    if session.expires_on < datetime.utcnow().replace(microsecond=0):
        session.delete_instance()
        logger.debug(u"session %s is expired, deleted" % sid)
        return default
    
    return session


def delete_session(sid):
    Session.delete().where(Session.key==sid).execute()


def set_session(sid, value, timeout=SESSION_TIMEOUT):

    session = get_session(sid)
    if not session:
        # New session if sid not present
        session = Session(key=sid)
        logger.debug(u"session %s created" % sid)

    session.expires_on = (datetime.utcnow() + timedelta(seconds=timeout)).replace(microsecond=0)
    session.value = value
    session.save()