# -*- coding: utf-8 -*-
'''
Description: entry point for WSGI environments

Copyright (c) 2013— Andrea Peltrin
License: MIT (see LICENSE.md for details)
'''

from coldsweat.app import setup_app
app = setup_app()