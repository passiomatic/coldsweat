#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Description: bootstrap file for CGI environments

Copyright (c) 2013—2016 Andrea Peltrin
License: MIT (see LICENSE for details)
'''

from wsgiref.handlers import CGIHandler
from coldsweat.app import setup_app

if __name__ == '__main__':
    CGIHandler().run(setup_app())


