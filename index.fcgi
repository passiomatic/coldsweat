#!/usr/bin/env python

# -----------------------------------------------
# Index file for FastCGI environments
# -----------------------------------------------

from coldsweat import app

try:
    from flup.server.fcgi_fork import WSGIServer
except ImportError, ex:
    print 'Error: unable to import Flup package.\nColdsweat needs Flup to run as a FastCGI process.\nDownload it from PyPI: http://pypi.python.org/pypi/flup'
    raise ex

if __name__ == '__main__':
    WSGIServer(app.dispatch_request).run()



