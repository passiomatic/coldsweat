# -*- coding: utf-8 -*-
'''
Coldsweat - A Fever clone

Copyright (c) 2013—2014 Andrea Peltrin
Portions are copyright (c) 2013 Rui Carmo
License: MIT (see LICENSE.md for details)
'''

__author__ = 'Andrea Peltrin and Rui Carmo'
__version__ = (0, 9, 1, '')
__license__ = 'MIT'

from os import path
from ConfigParser import RawConfigParser
import logging
from webob.exc import status_map

VERSION_STRING = '%d.%d.%d%s' % __version__
         
# Figure out installation directory. This has 
#  to work for the fetcher script too
installation_dir, _ = path.split(path.dirname(path.abspath(__file__))) 
template_dir        = path.join(installation_dir, 'coldsweat/templates')

# Set up configuration settings
config = RawConfigParser()

config_path = path.join(installation_dir, 'etc/config')
if path.exists(config_path):
    config.read(config_path)
else:
    raise RuntimeError('Could not find configuration file %s' % config_path)

# ------------------------------------------------------
# User agent string
# ------------------------------------------------------

user_agent = 'Coldsweat/%s Feed Fetcher <http://lab.passiomatic.com/coldsweat/>' % VERSION_STRING
if config.has_option('fetcher', 'user_agent'):  
    user_agent = config.get('fetcher', 'user_agent')     

# ------------------------------------------------------
# Configure logger
# ------------------------------------------------------

log_level = config.get('log', 'level').upper()
logging.basicConfig(
    filename    = config.get('log', 'filename'),
    level       = getattr(logging, log_level),
    format      = config.get('log', 'format'),
    datefmt     = config.get('log', 'datefmt'),
)

for module in 'peewee', 'requests':
    logging.getLogger(module).setLevel(logging.CRITICAL if log_level != 'DEBUG' else logging.WARN)
        
# Shared logger instance
log = logging.getLogger()

# ------------------------------------------------------
# Custom error codes 9xx & exceptions 
# ------------------------------------------------------

class DuplicatedFeedError(Exception):
    code        = 900
    title       = 'Duplicated feed'
    explanation = 'Feed address matches another already present in the database.'

class ProblematicFeedError(Exception):
    code        = 901
    title       = 'Too many errors'
    explanation =  'Feed has accomulated too many parsing and/or network errors.'

for klass in (DuplicatedFeedError, ProblematicFeedError): 
    status_map[klass.code] = klass
