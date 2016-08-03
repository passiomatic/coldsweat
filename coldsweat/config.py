# -*- coding: utf-8 -*-
'''
Description: configuration settings

Copyright (c) 2013—2016 Andrea Peltrin
Portions are copyright (c) 2013 Rui Carmo
License: MIT (see LICENSE for details)
'''

import os
from ConfigParser import SafeConfigParser

from utilities import Struct

__all__ = [
    'load_config',
]

DEFAULTS = {
    'min_interval'      : '900',
    'max_errors'        : '50',
    'max_history'       : '7',
    'timeout'           : '10',
    'processes'         : '4',
    
    'level'             : 'INFO',
    'filename'          : '',       # Don't log
    
    'static_url'        : '',
    
    'load'              : ''
}

def load_config(config_path):
    '''
    Load up configuration settings
    '''
    parser = SafeConfigParser(DEFAULTS)

    converters = {
        'min_interval'  : parser.getint,
        'max_errors'    : parser.getint,
        'max_history'   : parser.getint,
        'timeout'       : parser.getint,
        'processes'     : parser.getint,
    }

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
        
    return config