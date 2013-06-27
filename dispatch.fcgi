#!/usr/bin/env python
"""
Boostrap file for FastCGI environments
"""

# -----------------------------------------------
# Set media base URL, no trailing slash please
# -----------------------------------------------

# If you have istalled Coldsweat under a dir, e.g. coldsweat
STATIC_URL = '/coldsweat/static'

# If you have installed Coldsweat on site root
#STATIC_URL = '/static'

# If you want to serve static stuff from a different server
#STATIC_URL = 'http://static.example.com/static'

try:
    from flup.server.fcgi_fork import WSGIServer
except ImportError, exc:
    print 'Error: unable to import Flup package.\nColdsweat needs Flup to run as a FastCGI process.\nDownload it from PyPI: http://pypi.python.org/pypi/flup'
    raise exc

from coldsweat.app import ColdsweatApp, ExceptionMiddleware

app = ExceptionMiddleware(ColdsweatApp(STATIC_URL))     

if __name__ == '__main__':
    WSGIServer(app).run()



