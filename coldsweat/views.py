# -*- coding: utf-8 -*-
"""
Description: web views

Copyright (c) 2013—, Andrea Peltrin
Portions are copyright (c) 2013, Rui Carmo
License: MIT (see LICENSE.md for details)
"""

from app import *
from models import *
import fetcher

#from coldsweat import log

# -------------------
# Index page
# -------------------

@view()
def index(request, filler):     
    message = u''

    return HTTP_OK, [], make_page('index.html', filler, locals())


