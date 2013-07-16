#!/usr/bin/env python
"""
Boostrap file for FastCGI environments
"""

# -----------------------------------------------
# Set media base URL, no trailing slash please
# -----------------------------------------------

try:
    from flup.server.fcgi_fork import WSGIServer
except ImportError, exc:
    print 'Error: unable to import Flup package.\nColdsweat needs Flup to run as a FastCGI process.\nDownload it from PyPI: http://pypi.python.org/pypi/flup'
    raise exc

from coldsweat.app import setup_app

if __name__ == '__main__':
    WSGIServer(setup_app()).run()



