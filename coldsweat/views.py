# -*- coding: utf-8 -*-
"""
Description: web views

Copyright (c) 2013—, Andrea Peltrin
Portions are copyright (c) 2013, Rui Carmo
License: MIT (see LICENSE.md for details)
"""


from utilities import *    
from app import *

# -------------------
# Index page
# -------------------

@view()
def index(request, filler):     
    return HTTP_OK, [], make_page('index.html', filler, locals())



