# -*- coding: utf-8 -*-
'''
Description: Scrubber plugin. Remove links and images from 
  feed entries according to given blacklist

Copyright (c) 2013—2016 Andrea Peltrin
License: MIT (see LICENSE for details)
'''

import os

from coldsweat import *
from coldsweat.plugins import *
from coldsweat import markup

DOMAINS = []    

@event('fetch_started')
def fetcher_started():
    if DOMAINS: return # Already initialized
    
    blacklist = getattr(config.plugins, 'scrubber_blacklist', '')
    
    if blacklist:
      DOMAINS.extend(blacklist.split(','))    
    
    if DOMAINS:
      logger.debug(u"scrubber plugin: loaded blacklist: %s" % ', '.join(DOMAINS))
    else:
      logger.info(u"scrubber plugin: blacklist is empty, nothing to do")
    
    
@event('entry_parsed')
def entry_parsed(entry, parsed_entry):
    if DOMAINS and ('html' in entry.content_type):
        entry.content = markup.scrub_html(entry.content, DOMAINS)    