# -*- coding: utf-8 -*-
'''
Description: plugins suppprt

Copyright (c) 2013—2016 Andrea Peltrin
Portions are copyright (c) 2013 Rui Carmo
License: MIT (see LICENSE for details)
'''

import imp

from coldsweat import *

# Define an informal API for plugin implementations

__all__ = [
    'event',
]

def event(name):
    def _(handler):
        FETCHER_EVENTS[name].append(handler)
        return handler
    return _

# These are used internally by Coldsweat

FETCHER_EVENTS = {}
for name in 'entry_parsed fetch_started fetch_done'.split():
    FETCHER_EVENTS[name] = []

def trigger_event(name, *args):
    for handler in FETCHER_EVENTS[name]:
        handler(*args)
        
def load_plugins():
    '''
    Load plugins listed in config file
    '''
    if not config.plugins.load:
        return
        
    for name in config.plugins.load.split(','):
        name = name.strip()
        try:
            fp, pathname, description = imp.find_module(name, [plugin_dir])
            imp.load_module(name, fp, pathname, description)
        except ImportError, ex:
            logger.warn(u'could not load %s plugin (%s), ignored' % (name, ex))
            continue
        
        logger.debug('loaded %s plugin' % name)
        fp.close()
