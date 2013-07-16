#!/usr/bin/env python
"""
Boostrap file for CGI environments
"""

# -----------------------------------------------
# Set media base URL, no trailing slash please
# -----------------------------------------------

from wsgiref.handlers import CGIHandler
from coldsweat.app import setup_app

if __name__ == '__main__':
    CGIHandler().run(setup_app())


