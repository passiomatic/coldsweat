#!/usr/bin/env python

# -----------------------------------------------
# Index file for CGI environments
# -----------------------------------------------

from wsgiref.handlers import CGIHandler
from coldsweat import app

if __name__ == '__main__':
    CGIHandler().run(app.dispatch_request)


