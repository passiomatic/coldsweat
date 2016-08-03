#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Description: bootstrap file for FastCGI environments

Copyright (c) 2013—2016 Andrea Peltrin
License: MIT (see LICENSE for details)
'''

try:
    from flup.server.fcgi_fork import WSGIServer
except ImportError, exc:
    print 'Error: unable to import Flup package.\nColdsweat needs Flup to run as a FastCGI process.\nDownload it from PyPI: http://pypi.python.org/pypi/flup'
    raise exc

from coldsweat.app import setup_app

if __name__ == '__main__':
    WSGIServer(setup_app()).run()
