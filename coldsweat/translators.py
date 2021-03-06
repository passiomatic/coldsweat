# -*- coding: utf-8 -*-
'''
Description: translates feed and entries fields to Coldsweat nomenclature

Copyright (c) 2013—2016 Andrea Peltrin
License: MIT (see LICENSE for details)
'''
#import sys, os, re, time, urlparse

from coldsweat import *
from utilities import *

from models import *

import markup

__all__ = [
    'FeedTranslator',
    'EntryTranslator'
]

class FeedTranslator(object):

    def __init__(self, feed_dict):
        self.feed_dict = feed_dict
        
    def get_timestamp(self, default):
        for header in ['published_parsed', 'updated_parsed']:
            value = self.feed_dict.get(header, None)
            if value:
                # Fix future dates
                return min(tuple_as_datetime(value), default)
        logger.debug(u'no feed timestamp found, using default')    
        return default

    # Nullable fields
    
    def get_author(self):
        if 'name' in self.feed_dict.get('author_detail', []):
            return self.feed_dict.author_detail.name
        return None
    
    def get_alternate_link(self):        
        return self.feed_dict.get('link', None)
        
    def get_title(self):
        if 'title' in self.feed_dict:
            return truncate(markup.strip_html(self.feed_dict.title), Feed.MAX_TITLE_LENGTH)
        return None


class EntryTranslator(object):

    def __init__(self, entry_dict):
        self.entry_dict = entry_dict
    
    def get_guid(self, default):
        """
        Get a useful GUID from a feed entry
        """    
        value = getattr(self.entry_dict, 'id', None)
        return value or default

    def get_timestamp(self, default):
        """
        Select the best timestamp for an entry
        """
        for header in ['published_parsed', 'created_parsed', 'updated_parsed']:
            value = self.entry_dict.get(header, None)
            if value:
                # Fix future dates
                return min(tuple_as_datetime(value), default)
        logger.debug(u'no entry timestamp found, using default')    
        return default
            
    def get_title(self, default):
        if 'title' in self.entry_dict:
            return truncate(markup.strip_html(self.entry_dict.title), Entry.MAX_TITLE_LENGTH)
        return default

    def get_source(self):
#         d = self.entry_dict.get('source')
#         d['link']      
        return ''
    
    def get_content(self, default):
        """
        Select the best content from an entry
        """    
        candidates = self.entry_dict.get('content', [])
        if 'summary_detail' in self.entry_dict:
            candidates.append(self.entry_dict.summary_detail)
        for c in candidates:
            # Match text/html, application/xhtml+xml
            if 'html' in c.type:
                return c.type, c.value
        # Return first result, regardless of MIME type
        if candidates:
            return candidates[0].type, candidates[0].value
    
        logger.debug(u'no entry content found, using default')    
        return default
        
    # Nullable fields
    
    def get_link(self):
        # Special case for FeedBurner entries, see: http://bit.ly/1gRAvJv
        if 'feedburner_origlink' in self.entry_dict:
            return scrub_url(self.entry_dict.feedburner_origlink)
        if 'link' in self.entry_dict:
            return scrub_url(self.entry_dict.link)
        return None
        
    def get_author(self):  
        if 'name' in self.entry_dict.get('author_detail',[]):
            return self.entry_dict.author_detail.name     
        return None
