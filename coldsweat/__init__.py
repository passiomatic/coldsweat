# -*- coding: utf-8 -*-
'''
Coldsweat - RSS aggregator and web reader compatible with the Fever API

Copyright (c) 2013—2016 Andrea Peltrin
Portions are copyright (c) 2013 Rui Carmo
License: MIT (see LICENSE for details)
'''

__author__ = 'Andrea Peltrin and Rui Carmo'
__version__ = (0, 9, 8, '')
__license__ = 'MIT'

import os
import logging
from .config import load_config

__all__ = [
    'VERSION_STRING',
    'USER_AGENT',

    # Synthesized entries and feed URI's
    'FEED_TAG_URI',
    'ENTRY_TAG_URI',

    # Configuration
    'installation_dir',
    'template_dir',
    'config',

    # Logging
    'logger',
]

VERSION_STRING = '%d.%d.%d%s' % __version__
USER_AGENT = ('Coldsweat/%s Feed Fetcher <http://lab.passiomatic.com/'
              'coldsweat/>' % VERSION_STRING)

FEED_TAG_URI = 'tag:lab.passiomatic.com,2017:coldsweat:feed:%s'
ENTRY_TAG_URI = 'tag:lab.passiomatic.com,2017:coldsweat:entry:%s'

# Figure out installation directory. This has
#  to work for the fetcher script too

installation_dir = os.environ.get("COLDSWEAT_INSTALL_DIR")

if not installation_dir:
    installation_dir, _ = os.path.split(
        os.path.dirname(os.path.abspath(__file__)))

template_dir = os.path.join(installation_dir, 'coldsweat/templates')

# ------------------------------------------------------
# Load up configuration settings
# ------------------------------------------------------

config_path = os.environ.get("COLDSWEAT_CONFIG_PATH")

if not config_path:
    config_path = os.path.join(installation_dir, 'config')

config = load_config(config_path)

# ------------------------------------------------------
# Configure logger
# ------------------------------------------------------

# Shared logger instance
for module in 'peewee', 'requests':
    logging.getLogger(module).setLevel(logging.WARN)

logger = logging.getLogger()

if config.log.filename == 'stderr':
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(config.log.level)
elif config.log.filename:
    logging.basicConfig(
        filename=config.log.filename,
        level=getattr(logging, config.log.level),
        format='[%(asctime)s] %(process)d %(levelname)s %(message)s',
    )
else:
    # Silence is golden
    logger.addHandler(logging.NullHandler())
