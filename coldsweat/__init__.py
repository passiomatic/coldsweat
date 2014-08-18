# -*- coding: utf-8 -*-
'''
Coldsweat - Web RSS aggregator and reader compatible with the Fever API 

Copyright (c) 2013—2014 Andrea Peltrin
Portions are copyright (c) 2013 Rui Carmo
License: MIT (see LICENSE for details)
'''

__author__ = 'Andrea Peltrin and Rui Carmo'
__version__ = (0, 9, 3, '')
__license__ = 'MIT'

import os
import logging
from ConfigParser import SafeConfigParser
from utilities import Struct
from webob.exc import status_map

__all__ = [
    'VERSION_STRING',
    # Configuration
    'installation_dir',
    'template_dir',
    'plugin_dir',
    'config',
    # Logging
    'logger',
    # Plugins
    'event',
    'trigger_event',
    # Misc
    'DuplicatedFeedError'
]

VERSION_STRING = '%d.%d.%d%s' % __version__

         
# Figure out installation directory. This has 
#  to work for the fetcher script too
installation_dir, _ = os.path.split(os.path.dirname(os.path.abspath(__file__))) 
template_dir        = os.path.join(installation_dir, 'coldsweat/templates')
plugin_dir          = os.path.join(installation_dir, 'plugins')


# ------------------------------------------------------
# Configuration settings
# ------------------------------------------------------

defaults = {
    'min_interval'      : '900',
    'error_threshold'   : '50',
    'max_history'       : '7',
    'timeout'           : '10',
    'multiprocessing'   : 'on',
    'user_agent'        : 'Coldsweat/%s Feed Fetcher <http://lab.passiomatic.com/coldsweat/>' % VERSION_STRING,
    
    'level'             : 'INFO',
    'filename'          : '',       # Don't log
    
    'static_url'        : '',
    
    'load'              : ''
}

# Set up configuration settings
parser = SafeConfigParser(defaults)

converters = {
    'min_interval'      : parser.getint,
    'error_threshold'   : parser.getint,
    'max_history'       : parser.getint,
    'timeout'           : parser.getint,
    'multiprocessing'   : parser.getboolean,
}

config_path = os.path.join(installation_dir, 'etc/config')
if os.path.exists(config_path):
    parser.read(config_path)
else:
    raise RuntimeError('Could not find configuration file %s' % config_path)

config = Struct()
for section in parser.sections():
    d = { k : 
        converters[k](section, k) if k in converters else v 
        for k, v in parser.items(section)
    }    
    config[section] = Struct(d)
    
del parser

# ------------------------------------------------------
# Configure logger
# ------------------------------------------------------

# Shared logger instance
logger = logging.getLogger()

if config.log.filename:
    logging.basicConfig(
        filename    = config.log.filename,
        level       = getattr(logging, config.log.level),
        format      = '[%(asctime)s] %(process)d %(levelname)s %(message)s',
    )
    # Silence is golden
    for module in 'peewee', 'requests':        
        logging.getLogger(module).setLevel(logging.WARN)
else: 
    logger.addHandler(logging.NullHandler())


# ------------------------------------------------------
# Custom error codes 9xx & exceptions 
# ------------------------------------------------------

class DuplicatedFeedError(Exception):
    code        = 900
    title       = 'Duplicated feed'
    explanation = 'Feed address matches another already present in the database.'

# class ProblematicFeedError(Exception):
#     code        = 901
#     title       = 'Too many errors'
#     explanation =  'Feed has accomulated too many parsing and/or network errors.'

for klass in (DuplicatedFeedError,): 
    status_map[klass.code] = klass


# ------------------------------------------------------
# Plugins machinery
# ------------------------------------------------------

FETCHER_EVENTS = {}
for name in 'entry_parsed fetch_started fetch_done'.split():
    FETCHER_EVENTS[name] = []

def event(name):
    def _(handler):
        FETCHER_EVENTS[name].append(handler)
        return handler
    return _

def trigger_event(name, *args):
    for handler in FETCHER_EVENTS[name]:
        handler(*args)
