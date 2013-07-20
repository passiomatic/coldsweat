#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Description: test server

Copyright (c) 2013— Andrea Peltrin
License: MIT (see LICENSE.md for details)
'''
import optparse
from wsgiref.simple_server import make_server
from webob.static import DirectoryApp

from coldsweat.app import ExceptionMiddleware
from coldsweat.fever import fever_app
from coldsweat.frontend import frontend_app
from coldsweat.cascade import Cascade

static_app = DirectoryApp("static", index_page=None)

# Create a cascade that looks for static files first, 
#  then tries the other apps
cascade_app = ExceptionMiddleware(Cascade([static_app, fever_app, frontend_app]))

if __name__ == '__main__':

    parser = optparse.OptionParser(
        usage='%prog --port=PORT'
        )
    parser.add_option(
        '-p', '--port',
        default='8080',
        dest='port',
        type='int',
        help='Port to serve on (default 8080)')

    options, args = parser.parse_args()

    httpd = make_server('localhost', options.port, cascade_app)
    print 'Serving on http://localhost:%s' % options.port
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print 'Interrupted by user.'