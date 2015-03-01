# -*- coding: utf-8 -*-
'''
Coldsweat - RSS aggregator and web reader compatible with the Fever API 

Copyright (c) 2013—2014 Andrea Peltrin
Portions are copyright (c) 2013 Rui Carmo
License: MIT (see LICENSE for details)
'''

__author__ = 'Andrea Peltrin and Rui Carmo'
__version__ = (0, 9, 4, '')
__license__ = 'MIT'

import os
import logging
from config import *

# Define an informal API for plugin implementations

__all__ = [
    'VERSION_STRING',
    'USER_AGENT',
    # Configuration
    'installation_dir',
    'template_dir',
    'plugin_dir',
    'config',
    # Logging
    'logger',
]

VERSION_STRING  = '%d.%d.%d%s' % __version__
USER_AGENT      = 'Coldsweat/%s Feed Fetcher <http://lab.passiomatic.com/coldsweat/>' % VERSION_STRING
         
# Figure out installation directory. This has 
#  to work for the fetcher script too
installation_dir, _ = os.path.split(os.path.dirname(os.path.abspath(__file__))) 
template_dir        = os.path.join(installation_dir, 'coldsweat/templates')
plugin_dir          = os.path.join(installation_dir, 'plugins')

# ------------------------------------------------------
# Load up configuration settings
# ------------------------------------------------------

config = load_config(os.path.join(installation_dir, 'etc/config'))

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
    for module in 'peewee', 'requests':        
        logging.getLogger(module).setLevel(logging.WARN)
else:
    # Silence is golden 
    logger.addHandler(logging.NullHandler())


