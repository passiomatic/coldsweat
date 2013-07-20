#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Description: bootstrap file for CGI environments

Copyright (c) 2013— Andrea Peltrin
License: MIT (see LICENSE.md for details)
'''

from wsgiref.handlers import CGIHandler

from coldsweat.app import ExceptionMiddleware
from coldsweat.fever import fever_app
from coldsweat.frontend import frontend_app
from coldsweat.cascade import Cascade

app = ExceptionMiddleware(Cascade([fever_app, frontend_app]))

if __name__ == '__main__':
    CGIHandler().run(app)


